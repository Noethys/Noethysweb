# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Fusion de fiches familles et de fiches individuelles saisies en double.

Principe :
    - Toutes les données rattachées à la fiche absorbée (inscriptions, consommations, prestations, factures,
      règlements, pièces, historique...) sont réaffectées à la fiche conservée.
    - La réaffectation est générique (parcours de _meta.related_objects) : les tables ajoutées plus tard
      ou par des plugins sont prises en charge automatiquement.
    - Quelques tables font l'objet d'un dédoublonnage métier (rattachements, liens, questionnaires, inscriptions,
      vaccins, informations, scolarité, assurances, contacts d'urgence, payeurs).
    - Les champs vides de la fiche conservée sont complétés avec ceux de la fiche absorbée.
    - Tout est exécuté dans une transaction : en cas d'erreur, rien n'est modifié.
"""

import datetime, logging, re
from django.apps import apps as django_apps
from django.db import transaction, models, connection
from django.db.models import Count, Q
from core.models import Famille, Individu, Rattachement, Lien, Inscription, Consommation, QuestionnaireReponse, Vaccin, \
                        Information, Scolarite, Assurance, ContactUrgence, Payeur, Prestation, Facture, Reglement, Quotient, Mandat
from core.utils import utils_historique, utils_texte

logger = logging.getLogger(__name__)


class Erreur_fusion(Exception):
    pass


# Champs jamais recopiés d'une fiche à l'autre
CHAMPS_EXCLUS = {
    Famille: {"idfamille", "date_creation", "nom", "utilisateur", "internet_identifiant", "internet_mdp", "internet_secquest",
              "rue_resid", "cp_resid", "ville_resid", "secteur", "certification_date"},
    Individu: {"idindividu", "date_creation", "adresse_auto"},
}

# Champs texte concaténés plutôt que complétés
CHAMPS_CONCATENES = {"memo", "info_garde"}


def Autorise(utilisateur):
    """ Permissions nécessaires pour fusionner des fiches """
    if utilisateur.is_superuser:
        return True
    return utilisateur.has_perms(["core.famille_outils", "core.famille_prestations_modifier", "core.famille_reglements_modifier",
                                  "core.famille_factures_modifier", "core.individu_inscriptions_modifier"])


def Normaliser(texte):
    return " ".join(utils_texte.Supprimer_accents(texte or "").lower().replace("-", " ").split())


def Est_vide(valeur):
    return valeur is None or valeur == "" or (hasattr(valeur, "name") and not valeur.name)


CHAMPS_ADRESSE = {"rue_resid", "cp_resid", "ville_resid", "secteur"}


def Verifier_base():
    """ Sous MySQL, la fusion n'est possible que si toutes les tables sont en InnoDB (sinon pas de retour arrière en cas d'erreur) """
    if connection.vendor != "mysql":
        return
    tables = [modele._meta.db_table for modele in django_apps.get_app_config("core").get_models()]
    with connection.cursor() as cursor:
        cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND ENGINE <> 'InnoDB' AND TABLE_NAME IN (%s)" % ", ".join(["%s"] * len(tables)), tables)
        tables_non_transactionnelles = [ligne[0] for ligne in cursor.fetchall()]
    if tables_non_transactionnelles:
        raise Erreur_fusion("La fusion est impossible car certaines tables de la base ne sont pas au format InnoDB (%s). Contactez votre administrateur." % ", ".join(tables_non_transactionnelles[:5]))


def Remplacer_id_texte(texte, ancien, nouveau):
    """ Remplace un ID dans une liste d'ID stockée en texte ("12;15" ou "[12, 15]") en conservant son format. Renvoie None si inchangé. """
    ids = [int(valeur) for valeur in re.findall(r"\d+", texte or "")]
    if ancien not in ids:
        return None
    nouveaux_ids = []
    for idindividu in ids:
        idindividu = nouveau if idindividu == ancien else idindividu
        if idindividu not in nouveaux_ids:
            nouveaux_ids.append(idindividu)
    if texte.strip().startswith("["):
        return str(nouveaux_ids)
    separateur = re.search(r"\d+(\D+)\d+", texte)
    return (separateur.group(1) if separateur else ";").join(str(idindividu) for idindividu in nouveaux_ids)


def Corriger_listes_ids(ancien, nouveau):
    """ Corrige les listes d'individus stockées en texte (champ 'individus' des factures, attestations, devis, attestations fiscales...) """
    nbre = 0
    for modele in django_apps.get_app_config("core").get_models():
        try:
            champ = modele._meta.get_field("individus")
        except Exception:
            continue
        if champ.is_relation or not isinstance(champ, (models.CharField, models.TextField)):
            continue
        for pk, texte in modele._base_manager.filter(individus__contains=str(ancien)).values_list("pk", "individus"):
            nouveau_texte = Remplacer_id_texte(texte, ancien, nouveau)
            if nouveau_texte is not None:
                modele._base_manager.filter(pk=pk).update(individus=nouveau_texte)
                nbre += 1
    return nbre


# ---------------------------------------------------------------------------------------------------------------------
# Outils génériques
# ---------------------------------------------------------------------------------------------------------------------

def Get_relations(modele):
    """ Relations inverses (FK et M2M) pointant vers un modèle """
    return [rel for rel in modele._meta.related_objects if not rel.related_model._meta.proxy]


def Reaffecter(ancien, nouveau, apps=None):
    """ Réaffecte à 'nouveau' tous les enregistrements pointant vers 'ancien'. Renvoie {verbose_name_plural: nombre} """
    stats = {}
    for rel in Get_relations(type(ancien)):
        modele = rel.related_model
        if apps and modele._meta.app_label not in apps:
            continue

        # Clés étrangères
        if rel.one_to_many:
            nbre = modele._base_manager.filter(**{rel.field.name: ancien}).update(**{rel.field.name: nouveau})

        # OneToOne : transfert uniquement si la fiche conservée n'en possède pas déjà un
        elif rel.one_to_one:
            if modele._base_manager.filter(**{rel.field.name: nouveau}).exists():
                continue
            nbre = modele._base_manager.filter(**{rel.field.name: ancien}).update(**{rel.field.name: nouveau})

        # ManyToMany inverses (ex : Aide.individus, Famille.individus_masques)
        elif rel.many_to_many:
            through = rel.through
            champ_cible = rel.field.m2m_reverse_field_name()
            champ_source = rel.field.m2m_field_name()
            existants = set(through.objects.filter(**{champ_cible: nouveau}).values_list("%s_id" % champ_source, flat=True))
            nbre = 0
            for ligne in through.objects.filter(**{champ_cible: ancien}):
                if getattr(ligne, "%s_id" % champ_source) in existants:
                    ligne.delete()
                else:
                    setattr(ligne, champ_cible, nouveau)
                    ligne.save()
                    nbre += 1
        else:
            continue

        if nbre and modele is not Famille:
            label = str(modele._meta.verbose_name_plural).lower()
            stats[label] = stats.get(label, 0) + nbre
    return stats


def Fusionner_m2m(ancien, nouveau):
    """ Union des champs ManyToMany déclarés sur le modèle """
    for champ in type(ancien)._meta.many_to_many:
        valeurs = list(getattr(ancien, champ.name).all())
        if valeurs:
            getattr(nouveau, champ.name).add(*valeurs)


def Completer_champs(ancien, nouveau, exclus_supplementaires=()):
    """ Complète les champs vides de 'nouveau' avec ceux de 'ancien'. Renvoie la liste des libellés complétés """
    exclus = CHAMPS_EXCLUS.get(type(ancien), set()) | set(exclus_supplementaires)
    champs_completes = []
    for champ in type(ancien)._meta.concrete_fields:
        if champ.primary_key or champ.name in exclus or isinstance(champ, models.BooleanField):
            continue
        valeur_ancien = getattr(ancien, champ.attname)
        valeur_nouveau = getattr(nouveau, champ.attname)
        if Est_vide(valeur_ancien):
            continue
        if champ.name in CHAMPS_CONCATENES and not Est_vide(valeur_nouveau):
            if Normaliser(valeur_ancien) not in Normaliser(valeur_nouveau):
                setattr(nouveau, champ.attname, "%s\n%s" % (valeur_nouveau, valeur_ancien))
                champs_completes.append(str(champ.verbose_name))
        elif Est_vide(valeur_nouveau):
            setattr(nouveau, champ.attname, valeur_ancien.name if isinstance(champ, models.FileField) else valeur_ancien)
            champs_completes.append(str(champ.verbose_name))
    return champs_completes


def Liberer_fichiers(objet):
    """ Vide les champs fichiers en base (sans signal) pour que django-cleanup ne supprime pas un fichier transféré """
    champs = [champ.name for champ in type(objet)._meta.concrete_fields if isinstance(champ, models.FileField)]
    if champs:
        type(objet)._base_manager.filter(pk=objet.pk).update(**{champ: "" for champ in champs})


def Supprimer_doublon(garde, doublon):
    """ Supprime un enregistrement en double après avoir transféré ses dépendances et son éventuel document.
        Renvoie False si les deux enregistrements ont chacun un document différent (on les conserve alors tous les deux). """
    champs_fichiers = [champ for champ in type(garde)._meta.concrete_fields if isinstance(champ, models.FileField)]
    for champ in champs_fichiers:
        fichier_garde, fichier_doublon = getattr(garde, champ.name), getattr(doublon, champ.name)
        if fichier_garde and fichier_doublon and fichier_garde.name != fichier_doublon.name:
            return False
    modifie = False
    for champ in champs_fichiers:
        if not getattr(garde, champ.name) and getattr(doublon, champ.name):
            setattr(garde, champ.name, getattr(doublon, champ.name).name)
            modifie = True
    if modifie:
        garde.save()
    Reaffecter(doublon, garde)
    Liberer_fichiers(doublon)
    type(doublon)._base_manager.filter(pk=doublon.pk).delete()
    return True


def Dedoublonner(qs_gardes, qs_doublons, cle):
    """ Supprime les enregistrements de qs_doublons dont la clé existe déjà dans qs_gardes. Renvoie le nombre de suppressions """
    gardes = {}
    for objet in qs_gardes:
        gardes.setdefault(cle(objet), objet)
    nbre = 0
    for objet in qs_doublons:
        garde = gardes.get(cle(objet))
        if garde and garde.pk != objet.pk and Supprimer_doublon(garde, objet):
            nbre += 1
    return nbre


def Questionnaires_a_supprimer(qs_gardes, qs_doublons):
    """ Réponses aux questionnaires : la réponse de la fiche conservée est prioritaire si elle est renseignée """
    questions_renseignees = {reponse.question_id for reponse in qs_gardes if reponse.reponse not in (None, "") or reponse.choix_id}
    return [reponse.pk for reponse in qs_doublons if reponse.question_id in questions_renseignees or (reponse.reponse in (None, "") and not reponse.choix_id)]


def Periodes_chevauchent(debut1, fin1, debut2, fin2):
    """ Périodes qui se chevauchent ou se suivent (fin vide = période ouverte) """
    un_jour = datetime.timedelta(days=1)
    return (not fin2 or debut1 <= fin2 + un_jour) and (not fin1 or debut2 <= fin1 + un_jour)


# ---------------------------------------------------------------------------------------------------------------------
# Rapprochement des individus
# ---------------------------------------------------------------------------------------------------------------------

def Get_individus_famille(famille):
    return [rattachement.individu for rattachement in Rattachement.objects.select_related("individu").filter(famille=famille, individu__isnull=False).order_by("categorie", "individu__nom", "individu__prenom")]


def Score_ressemblance(individu1, individu2):
    """ 2 = certain (nom, prénom et date de naissance identiques), 1 = probable (nom et prénom identiques), 0 = aucun """
    if Normaliser(individu1.prenom) != Normaliser(individu2.prenom):
        return 0
    noms1 = {Normaliser(individu1.nom), Normaliser(individu1.nom_jfille)} - {""}
    noms2 = {Normaliser(individu2.nom), Normaliser(individu2.nom_jfille)} - {""}
    if not noms1 & noms2:
        return 0
    if individu1.date_naiss and individu2.date_naiss:
        return 2 if individu1.date_naiss == individu2.date_naiss else 0
    return 1


def Proposer_correspondances(individus_absorbes, individus_conserves):
    """ Renvoie {idindividu_absorbe: (idindividu_conserve, score)} """
    propositions = {}
    deja_pris = set()
    for individu in individus_absorbes:
        meilleur = None
        for candidat in individus_conserves:
            if candidat.pk == individu.pk or candidat.pk in deja_pris:
                continue
            score = Score_ressemblance(individu, candidat)
            if score and (not meilleur or score > meilleur[1]):
                meilleur = (candidat.pk, score)
        if meilleur:
            propositions[individu.pk] = meilleur
            deja_pris.add(meilleur[0])
    return propositions


def Rechercher_homonymes(individu, limite=20):
    """ Recherche dans toute la base les individus pouvant être des doublons de l'individu """
    prenom = Normaliser(individu.prenom)
    candidats = Individu.objects.filter(Q(nom__iexact=individu.nom) | Q(nom_jfille__iexact=individu.nom) | Q(nom__iexact=individu.nom_jfille or "-")).exclude(pk=individu.pk)
    resultats = [candidat for candidat in candidats if Normaliser(candidat.prenom) == prenom and Score_ressemblance(individu, candidat)]
    return resultats[:limite]


# ---------------------------------------------------------------------------------------------------------------------
# Analyses (aperçu avant fusion)
# ---------------------------------------------------------------------------------------------------------------------

def Compter_donnees_famille(famille):
    return {
        "Individus": Rattachement.objects.filter(famille=famille).count(),
        "Inscriptions": Inscription.objects.filter(famille=famille).count(),
        "Consommations": Consommation.objects.filter(inscription__famille=famille).count(),
        "Prestations": Prestation.objects.filter(famille=famille).count(),
        "Factures": Facture.objects.filter(famille=famille).count(),
        "Règlements": Reglement.objects.filter(famille=famille).count(),
        "Quotients": Quotient.objects.filter(famille=famille).count(),
    }


def Compter_donnees_individu(individu):
    return {
        "Familles": Rattachement.objects.filter(individu=individu).count(),
        "Inscriptions": Inscription.objects.filter(individu=individu).count(),
        "Consommations": Consommation.objects.filter(individu=individu).count(),
        "Prestations": Prestation.objects.filter(individu=individu).count(),
        "Informations": Information.objects.filter(individu=individu).count(),
        "Vaccins": Vaccin.objects.filter(individu=individu).count(),
    }


def Comparer_champs(ancien, nouveau):
    """ Liste des champs qui seront complétés ou qui diffèrent (la valeur conservée l'emporte) """
    exclus = CHAMPS_EXCLUS.get(type(ancien), set())
    resultats = []
    for champ in type(ancien)._meta.concrete_fields:
        if champ.primary_key or champ.name in exclus or isinstance(champ, (models.BooleanField, models.FileField)):
            continue
        valeur_ancien, valeur_nouveau = getattr(ancien, champ.name), getattr(nouveau, champ.name)
        if Est_vide(valeur_ancien):
            continue
        if Est_vide(valeur_nouveau):
            resultats.append({"label": str(champ.verbose_name), "conserve": "", "absorbe": Formater_valeur(ancien, champ), "action": "completer"})
        elif champ.name in CHAMPS_CONCATENES:
            if Normaliser(valeur_ancien) not in Normaliser(valeur_nouveau):
                resultats.append({"label": str(champ.verbose_name), "conserve": Formater_valeur(nouveau, champ), "absorbe": Formater_valeur(ancien, champ), "action": "concatener"})
        elif valeur_ancien != valeur_nouveau and Normaliser(str(valeur_ancien)) != Normaliser(str(valeur_nouveau)):
            resultats.append({"label": str(champ.verbose_name), "conserve": Formater_valeur(nouveau, champ), "absorbe": Formater_valeur(ancien, champ), "action": "ignorer"})
    return resultats


def Formater_valeur(objet, champ):
    if champ.choices:
        return getattr(objet, "get_%s_display" % champ.name)()
    valeur = getattr(objet, champ.name)
    if isinstance(valeur, datetime.datetime):
        return valeur.strftime("%d/%m/%Y %H:%M")
    if isinstance(valeur, datetime.date):
        return valeur.strftime("%d/%m/%Y")
    return str(valeur)


def Inscriptions_a_fusionner(individu_garde, individu_doublon, famille_doublon=None, famille_garde=None):
    """ Inscriptions du doublon qui seront fusionnées avec une inscription de l'individu conservé (même activité, même famille, périodes qui se chevauchent) """
    inscriptions_garde = list(Inscription.objects.select_related("activite", "groupe", "categorie_tarif").filter(individu=individu_garde))
    resultats = []
    for inscription in Inscription.objects.select_related("activite", "groupe", "categorie_tarif").filter(individu=individu_doublon):
        idfamille = famille_garde.pk if famille_doublon and inscription.famille_id == famille_doublon.pk else inscription.famille_id
        for inscription_garde in inscriptions_garde:
            if inscription_garde.activite_id == inscription.activite_id and inscription_garde.famille_id == idfamille and \
                    Periodes_chevauchent(inscription_garde.date_debut, inscription_garde.date_fin, inscription.date_debut, inscription.date_fin):
                resultats.append((inscription_garde, inscription))
                break
    return resultats


def Avertissements_inscriptions(paires):
    avertissements = []
    for garde, doublon in paires:
        if garde.groupe_id != doublon.groupe_id or garde.categorie_tarif_id != doublon.categorie_tarif_id:
            avertissements.append("Les inscriptions de %s à l'activité %s seront fusionnées mais n'ont pas le même groupe ou la même catégorie de tarif : "
                                  "le groupe « %s » et la catégorie « %s » de la fiche conservée seront appliqués." % (
                garde.individu.Get_nom(), garde.activite.nom, garde.groupe.nom, garde.categorie_tarif.nom))
    return avertissements


def Analyser_fusion_familles(famille_garde, famille_doublon):
    """ Aperçu de la fusion de deux familles """
    if famille_garde.pk == famille_doublon.pk:
        raise Erreur_fusion("Vous ne pouvez pas fusionner une famille avec elle-même.")

    individus_garde = Get_individus_famille(famille_garde)
    individus_doublon = Get_individus_famille(famille_doublon)
    ids_garde = {individu.pk for individu in individus_garde}
    propositions = Proposer_correspondances([individu for individu in individus_doublon if individu.pk not in ids_garde], individus_garde)

    lignes_individus = []
    for individu in individus_doublon:
        lignes_individus.append({
            "individu": individu,
            "deja_membre": individu.pk in ids_garde,
            "proposition": propositions.get(individu.pk, (None, 0))[0],
            "score": propositions.get(individu.pk, (None, 0))[1],
            "nbre_inscriptions": Inscription.objects.filter(individu=individu).count(),
        })

    avertissements = []
    if famille_doublon.utilisateur and famille_garde.utilisateur:
        avertissements.append("La famille absorbée possède un compte portail : il sera supprimé. Seul l'identifiant de la famille conservée restera valable.")
    elif famille_doublon.utilisateur:
        avertissements.append("Le compte portail de la famille absorbée sera transféré à la famille conservée, qui n'en possède pas.")
    if famille_garde.caisse_id and famille_doublon.caisse_id and famille_garde.caisse_id != famille_doublon.caisse_id:
        avertissements.append("Les deux familles ne sont pas rattachées à la même caisse : la caisse de la famille conservée sera appliquée.")
    if famille_garde.num_allocataire and famille_doublon.num_allocataire and famille_garde.num_allocataire != famille_doublon.num_allocataire:
        avertissements.append("Les numéros d'allocataire sont différents : celui de la famille conservée sera appliqué.")
    quotients_garde = list(Quotient.objects.filter(famille=famille_garde))
    for quotient in Quotient.objects.filter(famille=famille_doublon):
        if any(q.type_quotient_id == quotient.type_quotient_id and Periodes_chevauchent(q.date_debut, q.date_fin, quotient.date_debut, quotient.date_fin) for q in quotients_garde):
            avertissements.append("Certains quotients familiaux des deux familles portent sur des périodes qui se chevauchent : pensez à les vérifier après la fusion.")
            break
    if Mandat.objects.filter(famille=famille_garde, actif=True).exists() and Mandat.objects.filter(famille=famille_doublon, actif=True).exists():
        avertissements.append("Les deux familles possèdent un mandat de prélèvement SEPA actif : après la fusion, désactivez celui qui ne doit plus être utilisé (onglet Mandats).")
    if Facture.objects.filter(famille=famille_doublon).exists():
        avertissements.append("Les factures déjà éditées de la famille absorbée sont conservées avec leur numéro, mais seront désormais rattachées à la famille conservée.")

    stats_garde, stats_doublon = Compter_donnees_famille(famille_garde), Compter_donnees_famille(famille_doublon)
    return {
        "stats": [(label, stats_doublon[label], stats_garde[label]) for label in stats_garde],
        "individus_garde": individus_garde,
        "lignes_individus": lignes_individus,
        "comparaison": Comparer_champs(famille_doublon, famille_garde),
        "avertissements": avertissements,
    }


def Analyser_fusion_individus(individu_garde, individu_doublon):
    """ Aperçu de la fusion de deux individus """
    if individu_garde.pk == individu_doublon.pk:
        raise Erreur_fusion("Vous ne pouvez pas fusionner un individu avec lui-même.")
    paires = Inscriptions_a_fusionner(individu_garde, individu_doublon)
    avertissements = Avertissements_inscriptions(paires)
    if individu_garde.date_naiss and individu_doublon.date_naiss and individu_garde.date_naiss != individu_doublon.date_naiss:
        avertissements.insert(0, "Les dates de naissance sont différentes : vérifiez qu'il s'agit bien de la même personne.")
    if Normaliser(individu_garde.prenom) != Normaliser(individu_doublon.prenom):
        avertissements.insert(0, "Les prénoms sont différents : vérifiez qu'il s'agit bien de la même personne.")
    categories_garde = {r.famille_id: r.categorie for r in Rattachement.objects.filter(individu=individu_garde)}
    for rattachement in Rattachement.objects.filter(individu=individu_doublon):
        categorie_garde = categories_garde.get(rattachement.famille_id)
        if categorie_garde and categorie_garde != rattachement.categorie:
            avertissements.insert(0, "Attention : dans la même famille, ces deux fiches n'ont pas le même rôle (%s et %s). Vérifiez que vous n'êtes pas en train de fusionner deux personnes différentes." % (
                rattachement.get_categorie_display().lower(), dict(Rattachement._meta.get_field("categorie").choices).get(categorie_garde, "").lower()))
            break
    familles_doublon = [r.famille for r in Rattachement.objects.select_related("famille").filter(individu=individu_doublon, famille__isnull=False)]
    familles_garde = {r.famille_id for r in Rattachement.objects.filter(individu=individu_garde)}
    stats_garde, stats_doublon = Compter_donnees_individu(individu_garde), Compter_donnees_individu(individu_doublon)
    return {
        "stats": [(label, stats_doublon[label], stats_garde[label]) for label in stats_garde],
        "familles_doublon": [(famille, famille.pk in familles_garde) for famille in familles_doublon],
        "inscriptions_fusionnees": paires,
        "comparaison": Comparer_champs(individu_doublon, individu_garde),
        "avertissements": avertissements,
    }


# ---------------------------------------------------------------------------------------------------------------------
# Fusions
# ---------------------------------------------------------------------------------------------------------------------

class Rapport():
    def __init__(self):
        self.donnees = {}
        self.dedoublonnages = {}
        self.individus_fusionnes = []
        self.champs_completes = []
        self.avertissements = []

    def Ajouter_donnees(self, stats):
        for label, nbre in stats.items():
            self.donnees[label] = self.donnees.get(label, 0) + nbre

    def Ajouter_dedoublonnage(self, label, nbre):
        if nbre:
            self.dedoublonnages[label] = self.dedoublonnages.get(label, 0) + nbre

    def Get_texte(self):
        lignes = []
        if self.individus_fusionnes:
            lignes.append("Individus fusionnés : %s." % ", ".join(self.individus_fusionnes))
        if self.donnees:
            lignes.append("Données transférées : %s." % ", ".join("%d %s" % (nbre, label) for label, nbre in sorted(self.donnees.items())))
        if self.dedoublonnages:
            lignes.append("Doublons supprimés : %s." % ", ".join("%d %s" % (nbre, label) for label, nbre in sorted(self.dedoublonnages.items())))
        if self.champs_completes:
            lignes.append("Champs complétés : %s." % ", ".join(self.champs_completes))
        return "\n".join(lignes)


def _Fusionner_individus(individu_garde, individu_doublon, rapport, famille_garde=None, famille_doublon=None):
    """ Fusion de deux individus (à appeler dans une transaction) """
    individu_garde = Individu.objects.get(pk=individu_garde.pk)
    individu_doublon = Individu.objects.get(pk=individu_doublon.pk)

    # Adresse : si le doublon utilisait l'adresse d'un autre membre et que la fiche conservée n'a pas d'adresse, on reprend ce lien
    exclus = set()
    if individu_garde.adresse_auto == individu_garde.pk:
        individu_garde.adresse_auto = None
    if not individu_garde.adresse_auto and not individu_garde.rue_resid and individu_doublon.adresse_auto and individu_doublon.adresse_auto not in (individu_garde.pk, individu_doublon.pk):
        individu_garde.adresse_auto = individu_doublon.adresse_auto
        exclus = CHAMPS_ADRESSE
    elif individu_garde.adresse_auto:
        exclus = CHAMPS_ADRESSE

    # Champs de la fiche
    rapport.champs_completes += ["%s (%s)" % (label, individu_garde.Get_nom()) for label in Completer_champs(individu_doublon, individu_garde, exclus)]
    if individu_garde.photo and individu_doublon.photo and individu_garde.photo.name != individu_doublon.photo.name:
        rapport.avertissements.append("La photo de la fiche absorbée n'a pas été conservée car la fiche de %s en possédait déjà une." % individu_garde.Get_nom())
        stockage, nom_photo = individu_doublon.photo.storage, individu_doublon.photo.name
        transaction.on_commit(lambda: stockage.delete(nom_photo))
    individu_garde.save()
    Liberer_fichiers(individu_doublon)
    Fusionner_m2m(individu_doublon, individu_garde)

    # Rattachements : un seul rattachement par famille
    familles_garde = set(Rattachement.objects.filter(individu=individu_garde).values_list("famille_id", flat=True))
    nbre = Rattachement.objects.filter(individu=individu_doublon, famille_id__in=familles_garde).delete()[0]
    rapport.Ajouter_dedoublonnage("rattachements", nbre)

    # Inscriptions : fusion des inscriptions identiques
    for inscription_garde, inscription_doublon in Inscriptions_a_fusionner(individu_garde, individu_doublon, famille_doublon=famille_doublon, famille_garde=famille_garde):
        inscription_garde.date_debut = min(inscription_garde.date_debut, inscription_doublon.date_debut)
        inscription_garde.date_fin = None if not inscription_garde.date_fin or not inscription_doublon.date_fin else max(inscription_garde.date_fin, inscription_doublon.date_fin)
        if "ok" in (inscription_garde.statut, inscription_doublon.statut):
            inscription_garde.statut = "ok"
        inscription_garde.save()
        rapport.Ajouter_donnees(Reaffecter(inscription_doublon, inscription_garde))
        Inscription.objects.filter(pk=inscription_doublon.pk).delete()
        rapport.Ajouter_dedoublonnage("inscriptions", 1)

    # Réponses aux questionnaires
    ids = Questionnaires_a_supprimer(QuestionnaireReponse.objects.filter(individu=individu_garde), QuestionnaireReponse.objects.filter(individu=individu_doublon))
    rapport.Ajouter_dedoublonnage("réponses aux questionnaires", QuestionnaireReponse.objects.filter(pk__in=ids).delete()[0])

    # Données de la fiche individuelle
    rapport.Ajouter_dedoublonnage("vaccins", Dedoublonner(Vaccin.objects.filter(individu=individu_garde), Vaccin.objects.filter(individu=individu_doublon),
                                                       cle=lambda o: (o.type_vaccin_id, o.date)))
    rapport.Ajouter_dedoublonnage("informations", Dedoublonner(Information.objects.filter(individu=individu_garde), Information.objects.filter(individu=individu_doublon),
                                                            cle=lambda o: (o.categorie_id, Normaliser(o.intitule))))
    rapport.Ajouter_dedoublonnage("étapes de scolarité", Dedoublonner(Scolarite.objects.filter(individu=individu_garde), Scolarite.objects.filter(individu=individu_doublon),
                                                                   cle=lambda o: (o.ecole_id, o.date_debut, o.date_fin)))
    rapport.Ajouter_dedoublonnage("assurances", Dedoublonner(Assurance.objects.filter(individu=individu_garde), Assurance.objects.filter(individu=individu_doublon),
                                                          cle=lambda o: (o.famille_id, o.assureur_id, Normaliser(o.num_contrat))))
    rapport.Ajouter_dedoublonnage("contacts d'urgence", Dedoublonner(ContactUrgence.objects.filter(individu=individu_garde), ContactUrgence.objects.filter(individu=individu_doublon),
                                                                  cle=lambda o: (o.famille_id, Normaliser(o.nom), Normaliser(o.prenom))))

    # Réaffectation de toutes les autres données
    rapport.Ajouter_donnees(Reaffecter(individu_doublon, individu_garde))
    Individu.objects.filter(adresse_auto=individu_doublon.pk).update(adresse_auto=individu_garde.pk)
    nbre = Corriger_listes_ids(individu_doublon.pk, individu_garde.pk)
    if nbre:
        rapport.Ajouter_donnees({"documents édités (factures, attestations, devis)": nbre})
    Individu.objects.filter(pk=individu_garde.pk, adresse_auto=individu_garde.pk).update(adresse_auto=None)

    # Liens : suppression des liens en double ou d'un individu vers lui-même
    rapport.Ajouter_dedoublonnage("liens", Nettoyer_liens(individu=individu_garde))

    # Suppression de la fiche en double
    nom_doublon = "%s (ID%d)" % (individu_doublon.Get_nom(), individu_doublon.pk)
    Individu.objects.get(pk=individu_doublon.pk).delete()
    rapport.individus_fusionnes.append("%s fusionné avec %s (ID%d)" % (nom_doublon, individu_garde.Get_nom(), individu_garde.pk))

    # MAJ des adresses automatiques
    for individu in Individu.objects.filter(Q(adresse_auto=individu_garde.pk) | Q(pk=individu_garde.pk)):
        individu.Maj_infos()
    return individu_garde


def Nettoyer_liens(famille=None, individu=None):
    """ Supprime les liens en double et les liens d'un individu vers lui-même """
    conditions = Q(famille=famille) if famille else Q(individu_sujet=individu) | Q(individu_objet=individu)
    vus, a_supprimer = set(), []
    for lien in Lien.objects.filter(conditions).order_by("pk"):
        cle = (lien.famille_id, lien.individu_sujet_id, lien.individu_objet_id)
        if lien.individu_sujet_id == lien.individu_objet_id or cle in vus:
            a_supprimer.append(lien.pk)
        vus.add(cle)
    return Lien.objects.filter(pk__in=a_supprimer).delete()[0]


def Compter_doublons_consommations(individus):
    """ Nombre de consommations en double (même individu, même date, même unité) après la fusion """
    resultats = Consommation.objects.filter(individu__in=individus).values("individu", "date", "unite").annotate(nbre=Count("pk")).filter(nbre__gt=1)
    return sum(resultat["nbre"] - 1 for resultat in resultats)


def Fusionner_individus(individu_garde, individu_doublon, utilisateur=None):
    """ Fusionne deux individus. Renvoie le rapport. """
    if individu_garde.pk == individu_doublon.pk:
        raise Erreur_fusion("Vous ne pouvez pas fusionner un individu avec lui-même.")
    Verifier_base()
    rapport = Rapport()
    familles = set(Rattachement.objects.filter(Q(individu=individu_garde) | Q(individu=individu_doublon)).values_list("famille_id", flat=True))
    rapport.avertissements += Avertissements_inscriptions(Inscriptions_a_fusionner(individu_garde, individu_doublon))
    with transaction.atomic():
        individu_garde = _Fusionner_individus(individu_garde, individu_doublon, rapport)
        for famille in Famille.objects.filter(pk__in=familles):
            famille.Maj_infos()
            Nettoyer_liens(famille=famille)
        nbre = Compter_doublons_consommations([individu_garde])
        if nbre:
            rapport.avertissements.append("%d consommation(s) en double ont été détectées (même date et même unité). Utilisez le correcteur d'anomalies (menu Outils) pour les traiter." % nbre)
        texte = "Fusion de la fiche %s" % rapport.individus_fusionnes[0] + "\n" + rapport.Get_texte()
        utils_historique.Ajouter(titre="Fusion d'individus", detail=texte, utilisateur=utilisateur, individu=individu_garde.pk,
                                 famille=Rattachement.objects.filter(individu=individu_garde).values_list("famille_id", flat=True).first())
    return rapport


def Fusionner_familles(famille_garde, famille_doublon, correspondances={}, utilisateur=None):
    """ Fusionne deux familles. correspondances = {idindividu_doublon: idindividu_garde} pour les individus à fusionner. Renvoie le rapport. """
    if famille_garde.pk == famille_doublon.pk:
        raise Erreur_fusion("Vous ne pouvez pas fusionner une famille avec elle-même.")

    Verifier_base()
    rapport = Rapport()
    ids_garde = set(Rattachement.objects.filter(famille=famille_garde).values_list("individu_id", flat=True))
    ids_doublon = set(Rattachement.objects.filter(famille=famille_doublon).values_list("individu_id", flat=True))
    for iddoublon, idgarde in correspondances.items():
        if iddoublon not in ids_doublon or idgarde not in ids_garde or iddoublon in ids_garde:
            raise Erreur_fusion("Les correspondances d'individus ne sont pas valides. Veuillez recommencer.")
    if len(set(correspondances.values())) != len(correspondances):
        raise Erreur_fusion("Un même individu de la famille conservée ne peut pas être associé à plusieurs individus.")

    nom_doublon = "%s (ID%d)" % (famille_doublon.nom or "", famille_doublon.pk)
    for iddoublon, idgarde in correspondances.items():
        rapport.avertissements += Avertissements_inscriptions(Inscriptions_a_fusionner(Individu.objects.get(pk=idgarde), Individu.objects.get(pk=iddoublon),
                                                                                       famille_doublon=famille_doublon, famille_garde=famille_garde))

    with transaction.atomic():
        famille_garde = Famille.objects.select_for_update().get(pk=famille_garde.pk)
        famille_doublon = Famille.objects.select_for_update().get(pk=famille_doublon.pk)

        # 1. Champs de la fiche famille
        rapport.champs_completes += Completer_champs(famille_doublon, famille_garde)
        utilisateur_doublon = famille_doublon.utilisateur
        if utilisateur_doublon and not famille_garde.utilisateur:
            Famille.objects.filter(pk=famille_doublon.pk).update(utilisateur=None)
            famille_garde.utilisateur = utilisateur_doublon
            famille_garde.internet_identifiant = famille_doublon.internet_identifiant
            famille_garde.internet_mdp = famille_doublon.internet_mdp
            famille_garde.internet_secquest = famille_doublon.internet_secquest
            famille_garde.internet_actif = famille_doublon.internet_actif
            utilisateur_doublon = None
        famille_garde.save()
        Fusionner_m2m(famille_doublon, famille_garde)

        # 2. Dédoublonnages préalables (la fiche conservée est prioritaire)
        rapport.Ajouter_dedoublonnage("rattachements", Rattachement.objects.filter(famille=famille_doublon, individu_id__in=ids_garde).delete()[0])
        ids = Questionnaires_a_supprimer(QuestionnaireReponse.objects.filter(famille=famille_garde, individu__isnull=True),
                                         QuestionnaireReponse.objects.filter(famille=famille_doublon, individu__isnull=True))
        rapport.Ajouter_dedoublonnage("réponses aux questionnaires", QuestionnaireReponse.objects.filter(pk__in=ids).delete()[0])
        rapport.Ajouter_dedoublonnage("payeurs", Dedoublonner(Payeur.objects.filter(famille=famille_garde), Payeur.objects.filter(famille=famille_doublon),
                                                           cle=lambda o: Normaliser(o.nom)))

        # 3. Réaffectation de toutes les données de la famille
        rapport.Ajouter_donnees(Reaffecter(famille_doublon, famille_garde))

        # 4. Compte portail de la famille absorbée : ses données (messages, historique...) sont transférées au compte conservé
        if utilisateur_doublon:
            Famille.objects.filter(pk=famille_doublon.pk).update(utilisateur=None)
            Reaffecter(utilisateur_doublon, famille_garde.utilisateur, apps=["core"])
            utilisateur_doublon.delete()

        # 5. Fusion des individus en double
        for iddoublon, idgarde in correspondances.items():
            _Fusionner_individus(Individu.objects.get(pk=idgarde), Individu.objects.get(pk=iddoublon), rapport, famille_garde=famille_garde, famille_doublon=famille_doublon)

        # 6. Nettoyages et suppression de la famille absorbée
        rapport.Ajouter_dedoublonnage("liens", Nettoyer_liens(famille=famille_garde))
        Famille.objects.get(pk=famille_doublon.pk).delete()

        famille_garde = Famille.objects.get(pk=famille_garde.pk)
        if not Rattachement.objects.filter(famille=famille_garde, titulaire=True).exists():
            premier = Rattachement.objects.filter(famille=famille_garde, categorie=1).order_by("pk").first()
            if premier:
                premier.titulaire = True
                premier.save()
        famille_garde.Maj_infos()

        if Mandat.objects.filter(famille=famille_garde, actif=True).count() > 1:
            rapport.avertissements.append("La famille possède désormais plusieurs mandats SEPA actifs : désactivez celui qui ne doit plus être utilisé.")
        nbre = Compter_doublons_consommations(Individu.objects.filter(rattachement__famille=famille_garde))
        if nbre:
            rapport.avertissements.append("%d consommation(s) en double ont été détectées (même individu, même date et même unité). Utilisez le correcteur d'anomalies (menu Outils) pour les traiter." % nbre)

        texte = "Fusion de la famille %s dans la famille %s (ID%d)\n%s" % (nom_doublon, famille_garde.nom, famille_garde.pk, rapport.Get_texte())
        utils_historique.Ajouter(titre="Fusion de familles", detail=texte, utilisateur=utilisateur, famille=famille_garde.pk)

    return rapport
