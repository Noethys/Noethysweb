# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Moteur de l'assistant de saisie d'inscriptions par lot.

Les recherches sont faites directement en base sur des listes d'identifiants (values_list) : aucun objet n'est
instancié pour les milliers d'individus de la base. Les champs chiffrés (date de naissance, ville) ne sont
déchiffrés que pour les individus déjà présélectionnés, et uniquement quand un critère en a besoin.
"""

import datetime, json, logging, re, time, unicodedata
from collections import Counter
logger = logging.getLogger(__name__)
from django.db import transaction
from django.db.models import Q, Max, Count
from django.urls import reverse
from core.models import Activite, Groupe, CategorieTarif, Inscription, Rattachement, Individu, Famille, Scolarite, Ecole, \
                        NiveauScolaire, Tarif, Prestation, Consommation, Ventilation, MemoJournee
from core.utils import utils_dates, utils_historique

TAILLE_PAQUET = 900             # Taille des paquets d'identifiants pour les requêtes "IN" (compatible SQLite)
SEUIL_CHARGEMENT_COMPLET = 4000 # Au-delà, on lit toute la table plutôt que par paquets
NBRE_MAX_APERCU = 5000          # Nombre maximal d'individus affichables dans l'aperçu
CLE_SESSION = "assistant_inscriptions_lot"
LIBELLE_FONCTION = "Assistant de saisie d'inscriptions par lot"
PROFILS = [(2, "Enfants"), (1, "Représentants"), (3, "Contacts")]


class Erreur(Exception):
    pass


# ---------------------------------------------- Outils ----------------------------------------------

def Normaliser_texte(texte=""):
    """ Majuscules, sans accents ni espaces superflus : 'Landéda ' -> 'LANDEDA' """
    texte = unicodedata.normalize("NFKD", str(texte or ""))
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[\s\-']+", " ", texte)
    return texte.strip().upper()


def Get_date(valeur=None, obligatoire=False, nom="la date"):
    if not valeur:
        if obligatoire:
            raise Erreur("Veuillez renseigner %s" % nom)
        return None
    if isinstance(valeur, datetime.date):
        return valeur
    try:
        return datetime.date.fromisoformat(str(valeur)[:10])
    except ValueError:
        raise Erreur("%s n'est pas valide" % nom.capitalize())


def Get_entier(valeur=None):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def Get_liste_entiers(valeurs=None):
    return [x for x in (Get_entier(v) for v in (valeurs or [])) if x is not None]


def Par_paquets(liste=[]):
    liste = list(liste)
    for index in range(0, len(liste), TAILLE_PAQUET):
        yield liste[index:index + TAILLE_PAQUET]


def Get_valeurs(modele=None, ids=set(), champs=[]):
    """ Retourne {pk: (champs...)} pour les ids demandés, en lisant par paquets ou toute la table si nécessaire """
    ids = set(ids)
    resultats = {}
    if not ids:
        return resultats
    if len(ids) > SEUIL_CHARGEMENT_COMPLET:
        for ligne in modele.objects.values_list("pk", *champs):
            if ligne[0] in ids:
                resultats[ligne[0]] = ligne[1:]
    else:
        for paquet in Par_paquets(ids):
            for ligne in modele.objects.filter(pk__in=paquet).values_list("pk", *champs):
                resultats[ligne[0]] = ligne[1:]
    return resultats


def Calculer_age(date_naiss=None, date_reference=None):
    if not date_naiss or not date_reference:
        return None
    return date_reference.year - date_naiss.year - ((date_reference.month, date_reference.day) < (date_naiss.month, date_naiss.day))


def Get_activite(idactivite=None, request=None, nom="l'activité"):
    """ Retourne l'activité si elle est accessible à l'utilisateur """
    idactivite = Get_entier(idactivite)
    if not idactivite:
        raise Erreur("Veuillez sélectionner %s" % nom)
    activite = Activite.objects.filter(pk=idactivite, structure__in=request.user.structures.all()).first()
    if not activite:
        raise Erreur("%s n'est pas accessible" % nom.capitalize())
    return activite


def Lire_parametres(donnees=None):
    if isinstance(donnees, dict):
        return donnees
    try:
        parametres = json.loads(donnees or "{}")
    except ValueError:
        raise Erreur("Les paramètres ne sont pas valides")
    if not isinstance(parametres, dict):
        raise Erreur("Les paramètres ne sont pas valides")
    return parametres


# ---------------------------------------------- Activité ----------------------------------------------

def Get_infos_activite(activite=None):
    """ Résumé de l'activité de destination : groupes, places, catégories de tarifs, forfaits automatiques """
    inscrits_ok = {ligne["groupe"]: ligne["nbre"] for ligne in Inscription.objects.filter(activite=activite, statut="ok").values("groupe").annotate(nbre=Count("pk"))}
    groupes = [{"id": groupe.pk, "nom": groupe.nom, "max": groupe.nbre_inscrits_max or None, "inscrits": inscrits_ok.get(groupe.pk, 0)}
               for groupe in Groupe.objects.filter(activite=activite).order_by("ordre", "nom")]
    categories = [{"id": categorie.pk, "nom": categorie.nom} for categorie in CategorieTarif.objects.filter(activite=activite).order_by("nom")]
    forfaits = sorted(set(tarif.nom_tarif.nom for tarif in Get_tarifs_forfaits_auto(activite).select_related("nom_tarif")))
    return {
        "id": activite.pk,
        "nom": activite.nom,
        "date_debut": str(activite.date_debut) if activite.date_debut else "",
        "date_fin": str(activite.date_fin) if activite.date_fin else "",
        "date_debut_fr": utils_dates.ConvertDateToFR(activite.date_debut) if activite.date_debut else "",
        "date_fin_fr": utils_dates.ConvertDateToFR(activite.date_fin) if activite.date_fin else "",
        "max": activite.nbre_inscrits_max or None,
        "inscrits": sum(inscrits_ok.values()),
        "inscriptions": Inscription.objects.filter(activite=activite).count(),
        "groupes": groupes,
        "categories": categories,
        "forfaits": forfaits,
    }


def Get_tarifs_forfaits_auto(activite=None):
    """ Forfaits datés appliqués automatiquement à l'inscription (mêmes critères que utils_forfaits) """
    return Tarif.objects.filter(activite=activite, type="FORFAIT", forfait_saisie_auto=True, forfait_saisie_manuelle=False)


def Proposer_correspondances(origines=[], destinations=[]):
    """ Associe chaque élément d'origine à l'élément de destination de même nom (ou à l'unique destination) """
    index = {}
    for destination in destinations:
        index.setdefault(Normaliser_texte(destination["nom"]), destination["id"])
    resultats = {}
    for origine in origines:
        iddestination = index.get(Normaliser_texte(origine["nom"]))
        if not iddestination and len(destinations) == 1:
            iddestination = destinations[0]["id"]
        resultats[str(origine["id"])] = iddestination
    return resultats


def Get_infos_source(activite_source=None, activite=None):
    """ Groupes et catégories de l'activité d'origine avec les correspondances proposées """
    infos_destination = Get_infos_activite(activite)
    nbre_par_groupe = {ligne["groupe"]: ligne["nbre"] for ligne in Inscription.objects.filter(activite=activite_source).values("groupe").annotate(nbre=Count("pk"))}
    groupes = [{"id": groupe.pk, "nom": groupe.nom, "nbre": nbre_par_groupe.get(groupe.pk, 0)} for groupe in Groupe.objects.filter(activite=activite_source).order_by("ordre", "nom")]
    categories = [{"id": categorie.pk, "nom": categorie.nom} for categorie in CategorieTarif.objects.filter(activite=activite_source).order_by("nom")]
    return {
        "id": activite_source.pk,
        "nom": activite_source.nom,
        "date_fin": str(activite_source.date_fin) if activite_source.date_fin else "",
        "groupes": groupes,
        "categories": categories,
        "correspondances_groupes": Proposer_correspondances(groupes, infos_destination["groupes"]),
        "correspondances_categories": Proposer_correspondances(categories, infos_destination["categories"]),
    }


# ---------------------------------------------- Listes de référence ----------------------------------------------

def Get_villes():
    """ Villes de résidence présentes dans les fiches familles (pour les suggestions de saisie) """
    # Pour chaque ville, l'orthographe la plus fréquente est retenue (LANDÉDA plutôt que Landeda)
    orthographes = {}
    for ville in Famille.objects.values_list("ville_resid", flat=True):
        if ville and ville.strip():
            compteur = orthographes.setdefault(Normaliser_texte(ville), Counter())
            compteur[ville.strip().upper()] += 1
    return sorted((compteur.most_common(1)[0][0] for compteur in orthographes.values()), key=Normaliser_texte)


def Get_listes_scolarite():
    return {
        "ecoles": [{"id": ecole.pk, "nom": ecole.nom} for ecole in Ecole.objects.all().order_by("nom")],
        "niveaux": [{"id": niveau.pk, "nom": niveau.abrege or niveau.nom} for niveau in NiveauScolaire.objects.all().order_by("ordre")],
    }


def Rechercher_individus(texte=""):
    """ Recherche nominative pour l'ajout manuel d'individus """
    termes = [terme for terme in texte.split() if terme]
    if not termes or len(texte.strip()) < 2:
        return []
    condition = Q()
    for terme in termes[:4]:
        condition &= (Q(nom__icontains=terme) | Q(prenom__icontains=terme))
    individus = list(Individu.objects.filter(condition).values_list("pk", "nom", "prenom").order_by("nom", "prenom")[:20])
    familles = {}
    for idindividu, nom_famille in Rattachement.objects.filter(individu_id__in=[i[0] for i in individus]).values_list("individu_id", "famille__nom"):
        familles.setdefault(idindividu, []).append(nom_famille or "")
    return [{"id": idindividu, "label": Get_nom_complet(nom, prenom), "familles": ", ".join(sorted(set(familles.get(idindividu, []))))} for idindividu, nom, prenom in individus]


def Get_nom_complet(nom="", prenom=""):
    return ("%s %s" % ((nom or "").upper(), prenom or "")).strip()


def Resoudre_liste(texte=""):
    """ Associe chaque ligne "NOM Prénom" (ou "Prénom NOM") collée depuis un tableur à un individu """
    lignes = [ligne.strip() for ligne in re.split(r"[\r\n]+", texte or "") if ligne.strip()]
    if not lignes:
        return set(), [], []
    index = {}
    for idindividu, nom, prenom in Individu.objects.values_list("pk", "nom", "prenom"):
        for cle in (Normaliser_texte("%s %s" % (nom or "", prenom or "")), Normaliser_texte("%s %s" % (prenom or "", nom or ""))):
            index.setdefault(cle, set()).add(idindividu)
    trouves, non_trouves, ambigus = set(), [], []
    for ligne in lignes[:2000]:
        cle = Normaliser_texte(re.sub(r"[\t;,]+", " ", ligne))
        resultats = index.get(cle, set())
        if len(resultats) == 1:
            trouves |= resultats
        elif len(resultats) > 1:
            ambigus.append(ligne)
        else:
            non_trouves.append(ligne)
    return trouves, non_trouves, ambigus


# ---------------------------------------------- Recherche des candidats ----------------------------------------------

class Recherche():
    """ Applique la source et les critères, puis écarte les individus déjà inscrits.
    Résultat : self.paires = {(idindividu, idfamille): {"groupe_origine", "categorie_origine"}} """

    def __init__(self, parametres=None, request=None):
        self.p = Lire_parametres(parametres)
        self.request = request
        self.activite = Get_activite(self.p.get("idactivite"), request)
        self.date_debut = Get_date(self.p.get("date_debut")) or self.activite.date_debut or datetime.date.today()
        self.paires = {}
        self.deja_inscrits = {}
        self.non_trouves, self.ambigus = [], []
        self.nbre_sans_date_naiss = 0
        self.dates_naiss = {}
        self.villes_familles = {}
        self.source = self.p.get("source") or {}
        self.filtres = self.p.get("filtres") or {}
        self.Calculer()

    def Calculer(self):
        type_source = self.source.get("type")
        if type_source == "reinscription":
            self.Source_reinscription()
        elif type_source == "liste":
            self.Source_liste()
        elif type_source == "tous":
            if not (self.filtres.get("scolarite") or self.filtres.get("age") or self.filtres.get("villes")):
                raise Erreur("Ajoutez au moins un critère (scolarité, âge ou ville) pour limiter la sélection")
            self.Source_tous()
        else:
            raise Erreur("Veuillez choisir comment sélectionner les individus")

        if self.filtres.get("scolarite"):
            self.Filtre_scolarite(self.filtres["scolarite"])
        if self.filtres.get("villes"):
            self.Filtre_villes(self.filtres["villes"])
        if self.filtres.get("age"):
            self.Filtre_age(self.filtres["age"])

        # Mise à l'écart des individus déjà inscrits à l'activité sur la même famille
        existantes = set(Inscription.objects.filter(activite=self.activite).values_list("individu_id", "famille_id"))
        for paire in list(self.paires.keys()):
            if paire in existantes:
                self.deja_inscrits[paire] = self.paires.pop(paire)

    def Source_reinscription(self):
        activite_source = Get_activite(self.source.get("idactivite"), self.request, nom="l'activité d'origine")
        if activite_source.pk == self.activite.pk:
            raise Erreur("L'activité d'origine doit être différente de l'activité à laquelle vous inscrivez")
        inscriptions = Inscription.objects.filter(activite=activite_source)
        groupes = Get_liste_entiers(self.source.get("groupes"))
        if groupes:
            inscriptions = inscriptions.filter(groupe_id__in=groupes)
        elif "groupes" in self.source:
            raise Erreur("Cochez au moins un groupe d'origine")
        if self.source.get("actives_uniquement"):
            date_reference = Get_date(self.source.get("date_reference")) or self.date_debut - datetime.timedelta(days=1)
            inscriptions = inscriptions.filter(statut="ok").filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))
        for idindividu, idfamille, idgroupe, idcategorie in inscriptions.values_list("individu_id", "famille_id", "groupe_id", "categorie_tarif_id"):
            self.paires.setdefault((idindividu, idfamille), {"groupe_origine": idgroupe, "categorie_origine": idcategorie})

    def Source_liste(self):
        individus = set(Get_liste_entiers(self.source.get("individus")))
        trouves, self.non_trouves, self.ambigus = Resoudre_liste(self.source.get("texte", ""))
        individus |= trouves
        if not individus:
            if self.non_trouves or self.ambigus:
                return
            raise Erreur("Ajoutez au moins un individu à la liste")
        for paquet in Par_paquets(individus):
            for idindividu, idfamille in Rattachement.objects.filter(individu_id__in=paquet, famille__isnull=False).values_list("individu_id", "famille_id"):
                self.paires.setdefault((idindividu, idfamille), {})

    def Source_tous(self):
        profils = Get_liste_entiers(self.filtres.get("profils")) or [2]
        for idindividu, idfamille in Rattachement.objects.filter(categorie__in=profils, individu__isnull=False, famille__isnull=False).values_list("individu_id", "famille_id"):
            self.paires.setdefault((idindividu, idfamille), {})

    def Filtre_scolarite(self, filtre={}):
        date_scolarite = Get_date(filtre.get("date")) or self.date_debut
        scolarites = Scolarite.objects.filter(date_debut__lte=date_scolarite, date_fin__gte=date_scolarite)
        ecoles = Get_liste_entiers(filtre.get("ecoles"))
        if ecoles:
            scolarites = scolarites.filter(ecole_id__in=ecoles)
        niveaux = Get_liste_entiers(filtre.get("niveaux"))
        if niveaux:
            scolarites = scolarites.filter(niveau_id__in=niveaux)
        individus = set(scolarites.values_list("individu_id", flat=True))
        self.paires = {paire: valeur for paire, valeur in self.paires.items() if paire[0] in individus}

    def Filtre_villes(self, villes=[]):
        villes = {Normaliser_texte(ville) for ville in villes if Normaliser_texte(ville)}
        if not villes:
            return
        self.Charger_villes()
        self.paires = {paire: valeur for paire, valeur in self.paires.items() if Normaliser_texte(self.villes_familles.get(paire[1])) in villes}

    def Filtre_age(self, filtre={}):
        self.Charger_dates_naiss()
        if filtre.get("mode") == "naissance":
            date_min, date_max = Get_date(filtre.get("naiss_min"), nom="la date de naissance minimale"), Get_date(filtre.get("naiss_max"), nom="la date de naissance maximale")
            if not date_min and not date_max:
                raise Erreur("Renseignez au moins une date de naissance")
            def Valide(date_naiss):
                return (not date_min or date_naiss >= date_min) and (not date_max or date_naiss <= date_max)
        else:
            age_min, age_max = Get_entier(filtre.get("min")), Get_entier(filtre.get("max"))
            if age_min is None and age_max is None:
                raise Erreur("Renseignez au moins un âge")
            date_reference = Get_date(filtre.get("date")) or self.date_debut
            def Valide(date_naiss):
                age = Calculer_age(date_naiss, date_reference)
                return (age_min is None or age >= age_min) and (age_max is None or age <= age_max)
        resultats = {}
        sans_date = set()
        for paire, valeur in self.paires.items():
            date_naiss = self.dates_naiss.get(paire[0])
            if not date_naiss:
                sans_date.add(paire[0])
            elif Valide(date_naiss):
                resultats[paire] = valeur
        self.nbre_sans_date_naiss = len(sans_date)
        self.paires = resultats

    def Charger_dates_naiss(self, individus=None):
        individus = set(individus or [paire[0] for paire in self.paires]) - set(self.dates_naiss)
        for idindividu, (date_naiss,) in Get_valeurs(Individu, individus, ["date_naiss"]).items():
            self.dates_naiss[idindividu] = date_naiss

    def Charger_villes(self, familles=None):
        familles = set(familles or [paire[1] for paire in self.paires]) - set(self.villes_familles)
        for idfamille, (ville,) in Get_valeurs(Famille, familles, ["ville_resid"]).items():
            self.villes_familles[idfamille] = ville or ""

    def Get_individus(self):
        """ {idindividu: [idfamille, ...]} des candidats """
        individus = {}
        for idindividu, idfamille in self.paires:
            individus.setdefault(idindividu, []).append(idfamille)
        return individus

    def Get_compteurs(self):
        individus = self.Get_individus()
        par_groupe_origine = {}
        for idindividu, idfamille in self.paires:
            idgroupe = self.paires[(idindividu, idfamille)].get("groupe_origine")
            if idgroupe:
                par_groupe_origine[str(idgroupe)] = par_groupe_origine.get(str(idgroupe), 0) + 1
        return {
            "nbre": len(individus),
            "nbre_deja_inscrits": len({paire[0] for paire in self.deja_inscrits} - set(individus)),
            "nbre_plusieurs_familles": len([1 for familles in individus.values() if len(familles) > 1]),
            "nbre_sans_date_naiss": self.nbre_sans_date_naiss,
            "non_trouves": self.non_trouves[:50],
            "ambigus": self.ambigus[:50],
            "par_groupe_origine": par_groupe_origine,
        }


# ---------------------------------------------- Aperçu ----------------------------------------------

class Regles():
    """ Règles d'attribution du groupe et de la catégorie de tarif choisies à l'étape 3 """

    def __init__(self, parametres={}, infos_activite={}):
        self.groupes_valides = {groupe["id"] for groupe in infos_activite["groupes"]}
        self.categories_valides = {categorie["id"] for categorie in infos_activite["categories"]}
        regle_groupes = parametres.get("groupes") or {}
        regle_tarifs = parametres.get("tarifs") or {}
        self.mode_groupe = regle_groupes.get("mode", "unique")
        self.groupe_unique = self.Valider(regle_groupes.get("idgroupe"), self.groupes_valides)
        self.correspondances_groupes = {str(k): self.Valider(v, self.groupes_valides) for k, v in (regle_groupes.get("correspondances") or {}).items()}
        self.mode_tarif = regle_tarifs.get("mode", "unique")
        self.categorie_unique = self.Valider(regle_tarifs.get("idcategorie"), self.categories_valides)
        self.correspondances_categories = {str(k): self.Valider(v, self.categories_valides) for k, v in (regle_tarifs.get("correspondances") or {}).items()}
        self.categorie_ville = self.Valider(regle_tarifs.get("ville_categorie"), self.categories_valides)
        self.categorie_autre = self.Valider(regle_tarifs.get("autre_categorie"), self.categories_valides)
        self.villes = {Normaliser_texte(ville) for ville in (regle_tarifs.get("villes") or []) if Normaliser_texte(ville)}
        # Si l'activité n'a qu'un groupe ou une catégorie, c'est forcément celui-là
        if len(self.groupes_valides) == 1:
            self.groupe_unique = list(self.groupes_valides)[0]
        if len(self.categories_valides) == 1:
            self.categorie_unique = list(self.categories_valides)[0]

    def Valider(self, valeur=None, valides=set()):
        valeur = Get_entier(valeur)
        return valeur if valeur in valides else None

    def Get_groupe(self, origine={}):
        if len(self.groupes_valides) == 1:
            return self.groupe_unique
        if self.mode_groupe == "origine":
            return self.correspondances_groupes.get(str(origine.get("groupe_origine")))
        if self.mode_groupe == "unique":
            return self.groupe_unique
        return None

    def Get_categorie(self, origine={}, ville=""):
        if len(self.categories_valides) == 1:
            return self.categorie_unique
        if self.mode_tarif == "origine":
            return self.correspondances_categories.get(str(origine.get("categorie_origine")))
        if self.mode_tarif == "ville":
            return self.categorie_ville if Normaliser_texte(ville) in self.villes else self.categorie_autre
        if self.mode_tarif == "unique":
            return self.categorie_unique
        return None


def Get_apercu(parametres=None, request=None):
    recherche = Recherche(parametres, request)
    individus = recherche.Get_individus()
    if len(individus) > NBRE_MAX_APERCU:
        raise Erreur("La sélection contient %d individus : affinez-la (%d au maximum)" % (len(individus), NBRE_MAX_APERCU))

    infos_activite = Get_infos_activite(recherche.activite)
    regles = Regles(recherche.p, infos_activite)
    noms_groupes_origine = {}
    if recherche.source.get("type") == "reinscription":
        noms_groupes_origine = dict(Groupe.objects.filter(activite_id=Get_entier(recherche.source.get("idactivite"))).values_list("pk", "nom"))

    # Chargement des seules données utiles (déchiffrement limité aux candidats)
    tous_individus = set(individus) | {paire[0] for paire in recherche.deja_inscrits}
    toutes_familles = {paire[1] for paire in recherche.paires} | {paire[1] for paire in recherche.deja_inscrits}
    noms_individus = Get_valeurs(Individu, tous_individus, ["nom", "prenom"])
    noms_familles = Get_valeurs(Famille, toutes_familles, ["nom"])
    recherche.Charger_dates_naiss(individus)
    recherche.Charger_villes(toutes_familles)
    date_reference = recherche.date_debut

    lignes = []
    for idindividu, familles in individus.items():
        nom, prenom = noms_individus.get(idindividu, ("", ""))
        date_naiss = recherche.dates_naiss.get(idindividu)
        liste_familles = []
        for idfamille in sorted(familles, key=lambda idf: (noms_familles.get(idf, ("",))[0] or "")):
            origine = recherche.paires[(idindividu, idfamille)]
            ville = recherche.villes_familles.get(idfamille, "")
            liste_familles.append({
                "id": idfamille,
                "nom": noms_familles.get(idfamille, ("",))[0] or "Famille %d" % idfamille,
                "ville": (ville or "").upper(),
                "groupe": regles.Get_groupe(origine),
                "categorie_tarif": regles.Get_categorie(origine, ville),
                "groupe_origine": noms_groupes_origine.get(origine.get("groupe_origine"), ""),
            })
        famille = liste_familles[0] if len(liste_familles) == 1 else None
        lignes.append({
            "individu": idindividu,
            "nom": Get_nom_complet(nom, prenom),
            "tri": Normaliser_texte(Get_nom_complet(nom, prenom)),
            "age": Calculer_age(date_naiss, date_reference),
            "date_naiss": utils_dates.ConvertDateToFR(date_naiss) if date_naiss else "",
            "familles": liste_familles,
            "famille": famille["id"] if famille else None,
            "groupe": famille["groupe"] if famille else None,
            "categorie_tarif": famille["categorie_tarif"] if famille else None,
        })
    lignes.sort(key=lambda ligne: ligne["tri"])

    deja_inscrits = []
    for idindividu, idfamille in recherche.deja_inscrits:
        if idindividu in individus:
            continue
        nom, prenom = noms_individus.get(idindividu, ("", ""))
        deja_inscrits.append({"nom": Get_nom_complet(nom, prenom), "famille": noms_familles.get(idfamille, ("",))[0] or ""})
    deja_inscrits.sort(key=lambda ligne: Normaliser_texte(ligne["nom"]))

    return {"lignes": lignes, "deja_inscrits": deja_inscrits, "activite": infos_activite, "compteurs": recherche.Get_compteurs()}


# ---------------------------------------------- Génération ----------------------------------------------

class Collecteur_messages():
    """ Remplace le stockage des messages Django pendant l'application des forfaits : les messages
    sont mémorisés pour le compte rendu au lieu de s'accumuler dans la session de l'utilisateur """

    def __init__(self, request=None):
        self.user = getattr(request, "user", None)
        self.META = getattr(request, "META", {})
        self._messages = self
        self.liste = []

    def add(self, level, message, extra_tags=""):
        self.liste.append((level, str(message)))


def Valider_options(p={}, activite=None):
    date_debut = Get_date(p.get("date_debut"), obligatoire=True, nom="la date de début")
    date_fin = Get_date(p.get("date_fin"), nom="la date de fin")
    if date_fin and date_fin < date_debut:
        raise Erreur("La date de fin doit être supérieure à la date de début")
    if activite.date_fin and date_debut > activite.date_fin:
        raise Erreur("La date de début doit être inférieure à la date de fin de l'activité (%s)" % utils_dates.ConvertDateToFR(activite.date_fin))
    statut = p.get("statut") if p.get("statut") in ("ok", "attente") else "ok"
    return date_debut, date_fin, statut


def Generer(parametres=None, lignes=None, request=None):
    debut_traitement = time.time()
    p = Lire_parametres(parametres)
    activite = Get_activite(p.get("idactivite"), request)
    date_debut, date_fin, statut = Valider_options(p, activite)
    infos_activite = Get_infos_activite(activite)
    groupes_valides = {groupe["id"]: groupe for groupe in infos_activite["groupes"]}
    categories_valides = {categorie["id"]: categorie["nom"] for categorie in infos_activite["categories"]}

    # Lecture et validation des lignes envoyées par la page
    try:
        lignes = json.loads(lignes) if isinstance(lignes, str) else (lignes or [])
    except ValueError:
        raise Erreur("La liste des individus n'est pas valide")
    selection = {}
    for ligne in lignes:
        idindividu, idfamille = Get_entier(ligne.get("individu")), Get_entier(ligne.get("famille"))
        idgroupe, idcategorie = Get_entier(ligne.get("groupe")), Get_entier(ligne.get("categorie_tarif"))
        if not idindividu or not idfamille:
            raise Erreur("Choisissez une famille pour chaque individu coché")
        if idgroupe not in groupes_valides:
            raise Erreur("Choisissez un groupe pour chaque individu coché")
        if idcategorie not in categories_valides:
            raise Erreur("Choisissez une catégorie de tarif pour chaque individu coché")
        selection[(idindividu, idfamille)] = (idgroupe, idcategorie)
    if not selection:
        raise Erreur("Cochez au moins un individu à inscrire")

    # Vérification des rattachements et des inscriptions existantes
    rattachements = set()
    for paquet in Par_paquets({paire[0] for paire in selection}):
        rattachements |= set(Rattachement.objects.filter(individu_id__in=paquet).values_list("individu_id", "famille_id"))
    existantes = set(Inscription.objects.filter(activite=activite).values_list("individu_id", "famille_id"))
    ignores = 0
    for paire in list(selection):
        if paire not in rattachements:
            raise Erreur("Un des individus n'est pas rattaché à la famille indiquée. Actualisez l'aperçu.")
        if paire in existantes:
            del selection[paire]
            ignores += 1
    if not selection:
        raise Erreur("Tous les individus sélectionnés sont déjà inscrits à cette activité")

    # Noms pour le tri alphabétique et le compte rendu
    noms = {idindividu: Get_nom_complet(nom, prenom) for idindividu, (nom, prenom) in Get_valeurs(Individu, {paire[0] for paire in selection}, ["nom", "prenom"]).items()}
    paires_triees = sorted(selection, key=lambda paire: Normaliser_texte(noms.get(paire[0], "")))

    # Statuts : gestion des dépassements de capacité
    statuts = {paire: statut for paire in selection}
    if statut == "ok" and p.get("depassement") == "attente":
        places_groupes = {idgroupe: (groupe["max"] - groupe["inscrits"]) if groupe["max"] else None for idgroupe, groupe in groupes_valides.items()}
        places_activite = (infos_activite["max"] - infos_activite["inscrits"]) if infos_activite["max"] else None
        for paire in paires_triees:
            idgroupe = selection[paire][0]
            if places_groupes[idgroupe] is not None:
                if places_groupes[idgroupe] <= 0:
                    statuts[paire] = "attente"
                    continue
                places_groupes[idgroupe] -= 1
            if places_activite is not None:
                if places_activite <= 0:
                    statuts[paire] = "attente"
                    if places_groupes[idgroupe] is not None:
                        places_groupes[idgroupe] += 1
                    continue
                places_activite -= 1

    # Création des inscriptions et de l'historique
    internet_reservations = bool(p.get("internet_reservations", True))
    with transaction.atomic():
        pk_max = Inscription.objects.aggregate(pk_max=Max("pk"))["pk_max"] or 0
        Inscription.objects.bulk_create([Inscription(
            individu_id=paire[0], famille_id=paire[1], activite=activite, groupe_id=selection[paire][0], categorie_tarif_id=selection[paire][1],
            date_debut=date_debut, date_fin=date_fin, statut=statuts[paire], internet_reservations=internet_reservations,
        ) for paire in paires_triees])
        # Relecture des inscriptions créées (bulk_create ne renvoie pas les identifiants sous MySQL)
        inscriptions = {(i.individu_id, i.famille_id): i for i in Inscription.objects.filter(activite=activite, pk__gt=pk_max) if (i.individu_id, i.famille_id) in selection}

        libelles_statuts = dict(Inscription.statut_choix)
        actions = []
        for paire, inscription in inscriptions.items():
            detail = "Activité=%s, Groupe=%s, Catégorie de tarif=%s, Date de début=%s, Statut=%s (%s)" % (
                activite.nom, groupes_valides[inscription.groupe_id]["nom"], categories_valides[inscription.categorie_tarif_id],
                utils_dates.ConvertDateToFR(date_debut), libelles_statuts.get(inscription.statut, inscription.statut), LIBELLE_FONCTION)
            actions.append({"titre": "Ajouter une inscription", "detail": detail, "utilisateur": request.user, "famille_id": paire[1], "individu_id": paire[0],
                            "objet": "Inscription", "idobjet": inscription.pk, "classe": "Inscription", "activite_id": activite.pk})
        utils_historique.Ajouter_plusieurs(actions)

    # Application des forfaits datés (inscriptions validées uniquement, comme dans la fiche individuelle)
    forfaits_appliques, a_choisir, erreurs_forfaits = 0, [], []
    prestations_lot = []
    if p.get("appliquer_forfaits") and Get_tarifs_forfaits_auto(activite).exists():
        from individus.utils import utils_forfaits
        pk_max_prestation = Prestation.objects.aggregate(pk_max=Max("pk"))["pk_max"] or 0
        for paire in paires_triees:
            inscription = inscriptions.get(paire)
            if not inscription or inscription.statut != "ok":
                continue
            collecteur = Collecteur_messages(request)
            try:
                forfaits = utils_forfaits.Forfaits(request=collecteur, famille=paire[1], activites=[activite.pk], individus=[paire[0]])
                forfaits.Applique_forfait(mode_inscription=True, selection_activite=activite.pk)
            except Exception as err:
                logger.exception("Assistant inscriptions par lot : erreur pendant l'application d'un forfait")
                erreurs_forfaits.append({"nom": noms.get(paire[0], ""), "message": "Erreur pendant l'application du forfait : %s" % err})
                continue
            from django.contrib import messages
            forfaits_appliques += len([1 for niveau, message in collecteur.liste if niveau == messages.SUCCESS and message.startswith("Application du forfait")])
            for niveau, message in collecteur.liste:
                if niveau >= messages.WARNING:
                    erreurs_forfaits.append({"nom": noms.get(paire[0], ""), "message": message})
            if forfaits.montants_a_choisir:
                a_choisir.append({"nom": noms.get(paire[0], ""), "url": reverse("individu_appliquer_forfait_date_choix", kwargs={
                    "idfamille": paire[1], "idindividu": paire[0], "tarifs": ";".join(str(x) for x in forfaits.montants_a_choisir)})})
        individus_lot = {paire[0] for paire in inscriptions}
        prestations_lot = [pk for pk, idindividu in Prestation.objects.filter(pk__gt=pk_max_prestation, activite=activite).values_list("pk", "individu_id") if idindividu in individus_lot]

    # Mémorisation du lot pour permettre son annulation
    request.session[CLE_SESSION] = {
        "activite": activite.pk,
        "inscriptions": [inscription.pk for inscription in inscriptions.values()],
        "prestations": prestations_lot,
        "horodatage": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    en_attente = [{"nom": noms.get(paire[0], ""), "groupe": groupes_valides[inscription.groupe_id]["nom"],
                   "url": reverse("individu_inscriptions_modifier", kwargs={"idfamille": paire[1], "idindividu": paire[0], "pk": inscription.pk})}
                  for paire, inscription in sorted(inscriptions.items(), key=lambda x: Normaliser_texte(noms.get(x[0][0], ""))) if inscription.statut == "attente"]
    return {
        "nbre": len(inscriptions),
        "nbre_ok": len([1 for inscription in inscriptions.values() if inscription.statut == "ok"]),
        "nbre_attente": len(en_attente),
        "nbre_ignores": ignores,
        "en_attente": en_attente,
        "forfaits_appliques": forfaits_appliques,
        "a_choisir": a_choisir,
        "erreurs_forfaits": erreurs_forfaits[:200],
        "duree": round(time.time() - debut_traitement, 1),
        "activite": {"id": activite.pk, "nom": activite.nom},
        "date_debut": utils_dates.ConvertDateToFR(date_debut),
        "lignes": [{"nom": noms.get(paire[0], ""), "groupe": groupes_valides[inscription.groupe_id]["nom"],
                    "categorie": categories_valides[inscription.categorie_tarif_id], "statut": libelles_statuts.get(inscription.statut, "")}
                   for paire, inscription in sorted(inscriptions.items(), key=lambda x: Normaliser_texte(noms.get(x[0][0], "")))],
    }


# ---------------------------------------------- Annulation du dernier lot ----------------------------------------------

def Annuler_lot(request=None):
    lot = request.session.get(CLE_SESSION)
    if not lot or not lot.get("inscriptions"):
        raise Erreur("Aucun lot à annuler")
    activite = Get_activite(lot["activite"], request)
    inscriptions = list(Inscription.objects.select_related("individu").filter(pk__in=lot["inscriptions"], activite=activite))
    if not inscriptions:
        request.session.pop(CLE_SESSION, None)
        raise Erreur("Les inscriptions de ce lot ont déjà été supprimées")
    prestations_lot = set(lot.get("prestations", []))
    ids_inscriptions = [inscription.pk for inscription in inscriptions]
    paires = {(inscription.individu_id, inscription.famille_id) for inscription in inscriptions}

    # Contrôles : rien ne doit avoir été saisi ou facturé depuis la génération du lot
    blocages = set()
    for inscription_id in Consommation.objects.filter(inscription_id__in=ids_inscriptions).exclude(prestation_id__in=prestations_lot).values_list("inscription_id", flat=True):
        blocages.add(inscription_id)
    for inscription_id in MemoJournee.objects.filter(inscription_id__in=ids_inscriptions).values_list("inscription_id", flat=True):
        blocages.add(inscription_id)
    autres_prestations = Prestation.objects.filter(activite=activite, individu_id__in={paire[0] for paire in paires}).exclude(pk__in=prestations_lot)
    individus_bloques = {(idindividu, idfamille) for idindividu, idfamille in autres_prestations.values_list("individu_id", "famille_id")} & paires
    prestations_bloquees = set(Prestation.objects.filter(pk__in=prestations_lot, facture__isnull=False).values_list("individu_id", "famille_id"))
    prestations_bloquees |= set(Ventilation.objects.filter(prestation_id__in=prestations_lot).values_list("prestation__individu_id", "prestation__famille_id"))
    individus_bloques |= prestations_bloquees & paires
    noms_bloques = sorted({inscription.individu.Get_nom() for inscription in inscriptions if inscription.pk in blocages or (inscription.individu_id, inscription.famille_id) in individus_bloques})
    if noms_bloques:
        raise Erreur("Annulation impossible : des consommations, des prestations ou des règlements ont été saisis depuis pour %d individu(s) : %s%s" % (
            len(noms_bloques), ", ".join(noms_bloques[:10]), "..." if len(noms_bloques) > 10 else ""))

    with transaction.atomic():
        Consommation.objects.filter(inscription_id__in=ids_inscriptions).delete()
        Prestation.objects.filter(pk__in=prestations_lot).delete()
        actions = [{"titre": "Supprimer une inscription", "detail": "%s (annulation du lot - %s)" % (inscription, LIBELLE_FONCTION), "utilisateur": request.user,
                    "famille_id": inscription.famille_id, "individu_id": inscription.individu_id, "objet": "Inscription", "idobjet": inscription.pk,
                    "classe": "Inscription", "activite_id": activite.pk} for inscription in inscriptions]
        Inscription.objects.filter(pk__in=ids_inscriptions).delete()
        utils_historique.Ajouter_plusieurs(actions)
    request.session.pop(CLE_SESSION, None)
    return {"nbre": len(ids_inscriptions), "nbre_prestations": len(prestations_lot)}
