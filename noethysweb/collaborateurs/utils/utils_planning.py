# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from core.models import Collaborateur, EvenementCollaborateur, TypeEvenementCollaborateur, ContratCollaborateur, Ferie, Vacance
from core.utils import utils_parametres, utils_dates, utils_historique
from collaborateurs.utils.utils_affectations import Arbre

FORMAT_DATETIME = "%Y-%m-%d %H:%M"
CATEGORIE_PARAMETRES = "planning_equipe"
PERMISSION = "core.planning_equipe"

REGLAGES_DEFAUT = {
    "compact_auto": True, "compact_jours": 7, "compact_lignes": 60, "densite_auto": "compact",
    "repli_auto": True, "repli_jours": 7, "garder_deplies": "aujourdhui_premieres", "courbe_charge": True,
    "synthese_auto": True, "synthese_jours": 31, "synthese_mode": "proposer",
    "largeur_titre": 90, "largeur_horaires": 40,
    "tranche_jours": 7,
    "plage_auto": True, "plage_debut": 420, "plage_fin": 1140, "plage_marge": 30, "plage_min": 480,
    "pas": 15,
}

LIMITES_REGLAGES = {
    "compact_jours": (1, 366), "compact_lignes": (5, 5000), "repli_jours": (1, 366), "synthese_jours": (7, 732),
    "largeur_titre": (0, 600), "largeur_horaires": (0, 600), "tranche_jours": (1, 92),
    "plage_debut": (0, 1440), "plage_fin": (0, 1440), "plage_marge": (0, 240), "plage_min": (60, 1440), "pas": (1, 60),
}


def Parse_datetime(texte):
    return datetime.datetime.strptime(texte, FORMAT_DATETIME) if texte else None


def Parse_date(texte):
    return datetime.datetime.strptime(texte[:10], "%Y-%m-%d").date() if texte else None


def Format_datetime(valeur):
    return valeur.strftime(FORMAT_DATETIME) if valeur else None


# ------------------------------------------------- Droits -------------------------------------------------

def Get_ids_modifiables(user=None):
    """ Collaborateurs dont l'utilisateur peut modifier le planning : ceux des groupes qu'il supervise ou des groupes sans superviseur """
    if user.is_superuser:
        return set(Collaborateur.objects.values_list("pk", flat=True))
    conditions = Q(groupes__superviseurs=user) | Q(groupes__superviseurs__isnull=True)
    return set(Collaborateur.objects.filter(conditions).values_list("pk", flat=True).distinct())


def Peut_regler_pour_tous(user=None):
    return user.is_superuser or user.has_perm("core.types_evenements_collaborateurs_liste")


# ------------------------------------------------- Réglages -------------------------------------------------

def Nettoyer_reglages(reglages={}):
    """ Ne conserve que les clés connues avec des valeurs du bon type et dans les limites """
    resultat = {}
    for nom, defaut in REGLAGES_DEFAUT.items():
        if nom not in reglages:
            continue
        valeur = reglages[nom]
        try:
            if isinstance(defaut, bool):
                valeur = bool(valeur)
            elif isinstance(defaut, int):
                valeur = int(valeur)
                mini, maxi = LIMITES_REGLAGES.get(nom, (valeur, valeur))
                valeur = max(mini, min(maxi, valeur))
            else:
                valeur = str(valeur)[:50]
        except (TypeError, ValueError):
            continue
        resultat[nom] = valeur
    return resultat


def Get_reglages(user=None):
    """ Renvoie les réglages par défaut (pour tous) et ceux de l'utilisateur """
    defaut = dict(REGLAGES_DEFAUT)
    defaut.update(Nettoyer_reglages(utils_parametres.Get(nom="reglages", categorie=CATEGORIE_PARAMETRES, utilisateur=None, valeur={}) or {}))
    perso = Nettoyer_reglages(utils_parametres.Get(nom="reglages", categorie=CATEGORIE_PARAMETRES, utilisateur=user, valeur={}) or {})
    return {"defaut": defaut, "utilisateur": perso}


# ------------------------------------------------- Données -------------------------------------------------

def Get_dates_speciales(date_debut=None, date_fin=None):
    """ Jours fériés et périodes de vacances sur une période """
    feries = []
    liste_feries = list(Ferie.objects.all())
    date = date_debut
    while date <= date_fin:
        ferie = utils_dates.EstFerie(date, liste_feries)
        if ferie:
            feries.append({"date": str(date), "nom": ferie.nom})
        date += datetime.timedelta(days=1)
    vacances = [{"debut": str(vacance.date_debut), "fin": str(vacance.date_fin), "nom": "%s %s" % (vacance.nom, vacance.annee)}
                for vacance in Vacance.objects.filter(date_debut__lte=date_fin, date_fin__gte=date_debut).order_by("date_debut")]
    return {"feries": feries, "vacances": vacances}


def Serialiser_evenement(evenement=None):
    return {
        "id": evenement.pk, "c": evenement.collaborateur_id, "cat": evenement.type_evenement_id, "aff": evenement.affectation_id,
        "t": evenement.titre or "", "d": Format_datetime(evenement.date_debut), "f": Format_datetime(evenement.date_fin),
        "rd": Format_datetime(evenement.realise_debut), "rf": Format_datetime(evenement.realise_fin), "v": evenement.version,
    }


def Get_evenements(date_debut=None, date_fin=None, collaborateurs=None):
    """ Evènements qui touchent la période (dates incluses) """
    debut = datetime.datetime.combine(date_debut, datetime.time(0, 0))
    fin = datetime.datetime.combine(date_fin + datetime.timedelta(days=1), datetime.time(0, 0))
    conditions = Q(date_debut__lt=fin, date_fin__gt=debut)
    if collaborateurs is not None:
        conditions &= Q(collaborateur_id__in=collaborateurs)
    return EvenementCollaborateur.objects.filter(conditions).order_by("date_debut")


def Description_evenement(evenement=None, categories={}, arbre=None):
    """ Texte lisible pour l'historique """
    texte = "%s %s-%s" % (evenement.date_debut.strftime("%d/%m/%Y"), evenement.date_debut.strftime("%H:%M"), evenement.date_fin.strftime("%H:%M"))
    if evenement.date_fin.date() != evenement.date_debut.date():
        texte = "%s - %s" % (evenement.date_debut.strftime("%d/%m/%Y %H:%M"), evenement.date_fin.strftime("%d/%m/%Y %H:%M"))
    categorie = categories.get(evenement.type_evenement_id)
    if categorie:
        texte += " %s" % categorie.nom
    if evenement.titre:
        texte += " (%s)" % evenement.titre
    if evenement.affectation_id and arbre:
        texte += " - %s" % arbre.Get_chemin(evenement.affectation_id)
    return texte


# ------------------------------------------------- Enregistrement -------------------------------------------------

class Erreur_enregistrement(Exception):
    pass


def Verifier_chevauchements(evenements=[], categories={}):
    """ Vérifie qu'aucun évènement ne chevauche un autre évènement du même collaborateur (sauf catégories autorisées) """
    erreurs = []
    for evenement in evenements:
        if categories[evenement.type_evenement_id].chevauchement_possible:
            continue
        autres = EvenementCollaborateur.objects.filter(collaborateur_id=evenement.collaborateur_id, date_debut__lt=evenement.date_fin,
                                                       date_fin__gt=evenement.date_debut).exclude(pk=evenement.pk)
        for autre in autres:
            if not categories[autre.type_evenement_id].chevauchement_possible:
                erreurs.append({"id": evenement.pk, "message": "Chevauchement avec un autre évènement le %s" % evenement.date_debut.strftime("%d/%m/%Y")})
                break
    return erreurs


def Appliquer_donnees(evenement=None, donnees={}, categories={}, arbre=None):
    """ Applique un dictionnaire de données client à un évènement, avec validation """
    try:
        if "c" in donnees:
            evenement.collaborateur_id = int(donnees["c"])
        if "cat" in donnees:
            evenement.type_evenement_id = int(donnees["cat"])
        if "aff" in donnees:
            evenement.affectation_id = int(donnees["aff"]) if donnees["aff"] else None
        if "t" in donnees:
            evenement.titre = (donnees["t"] or "").strip()[:200] or None
        if "d" in donnees:
            evenement.date_debut = Parse_datetime(donnees["d"])
        if "f" in donnees:
            evenement.date_fin = Parse_datetime(donnees["f"])
        if "rd" in donnees or "rf" in donnees:
            evenement.realise_debut = Parse_datetime(donnees.get("rd"))
            evenement.realise_fin = Parse_datetime(donnees.get("rf"))
    except (TypeError, ValueError):
        raise Erreur_enregistrement("Données de l'évènement incorrectes")

    if not evenement.date_debut or not evenement.date_fin or evenement.date_fin <= evenement.date_debut:
        raise Erreur_enregistrement("L'heure de fin doit être postérieure à l'heure de début")
    if evenement.date_fin - evenement.date_debut > datetime.timedelta(days=31):
        raise Erreur_enregistrement("Un évènement ne peut pas dépasser 31 jours")
    if evenement.type_evenement_id not in categories:
        raise Erreur_enregistrement("La catégorie d'évènement est obligatoire")
    if evenement.affectation_id and evenement.affectation_id not in arbre.affectations:
        raise Erreur_enregistrement("L'affectation sélectionnée n'existe plus")
    if bool(evenement.realise_debut) != bool(evenement.realise_fin):
        raise Erreur_enregistrement("Saisissez à la fois le début et la fin du réalisé")
    if evenement.realise_debut and evenement.realise_fin <= evenement.realise_debut:
        raise Erreur_enregistrement("La fin du réalisé doit être postérieure à son début")


def Enregistrer_operations(operations=[], user=None):
    """ Applique un lot d'opérations (création, modification, suppression) dans une transaction.
        Lève Erreur_enregistrement en cas de problème (l'appelant annule la transaction). """
    ids_modifiables = Get_ids_modifiables(user)
    categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
    arbre = Arbre()
    ids_collaborateurs = set(Collaborateur.objects.values_list("pk", flat=True))

    ids_existants = [int(operation["id"]) for operation in operations if operation.get("op") in ("update", "delete")]
    existants = {evenement.pk: evenement for evenement in EvenementCollaborateur.objects.select_for_update().filter(pk__in=ids_existants)}

    resultat = {"crees": {}, "maj": {}, "supprimes": []}
    conflits = []
    a_verifier = []
    historique = []

    for operation in operations:
        action = operation.get("op")

        if action == "create":
            evenement = EvenementCollaborateur()
            Appliquer_donnees(evenement, operation.get("data", {}), categories, arbre)
            if evenement.collaborateur_id not in ids_collaborateurs:
                raise Erreur_enregistrement("Collaborateur inconnu")
            if evenement.collaborateur_id not in ids_modifiables:
                raise Erreur_enregistrement("Vous n'avez pas l'autorisation de modifier le planning de ce collaborateur")
            evenement.version = 1
            evenement.save()
            resultat["crees"][str(operation.get("tmp"))] = {"id": evenement.pk, "v": evenement.version}
            a_verifier.append(evenement)
            historique.append({"titre": "Ajout d'un évènement", "detail": Description_evenement(evenement, categories, arbre), "collaborateur_id": evenement.collaborateur_id,
                               "objet": "Evènement", "idobjet": evenement.pk, "classe": "EvenementCollaborateur", "utilisateur": user})

        elif action in ("update", "delete"):
            evenement = existants.get(int(operation["id"]))
            if not evenement or evenement.version != int(operation.get("v", 0)):
                conflits.append(int(operation["id"]))
                continue
            if evenement.collaborateur_id not in ids_modifiables:
                raise Erreur_enregistrement("Vous n'avez pas l'autorisation de modifier le planning de ce collaborateur")

            if action == "delete":
                historique.append({"titre": "Suppression d'un évènement", "detail": Description_evenement(evenement, categories, arbre), "collaborateur_id": evenement.collaborateur_id,
                                   "objet": "Evènement", "idobjet": evenement.pk, "classe": "EvenementCollaborateur", "utilisateur": user})
                evenement.delete()
                resultat["supprimes"].append(int(operation["id"]))
                continue

            ancien = Description_evenement(evenement, categories, arbre)
            ancien_collaborateur = evenement.collaborateur_id
            Appliquer_donnees(evenement, operation.get("data", {}), categories, arbre)
            if evenement.collaborateur_id not in ids_modifiables or evenement.collaborateur_id not in ids_collaborateurs:
                raise Erreur_enregistrement("Vous n'avez pas l'autorisation de modifier le planning de ce collaborateur")
            evenement.version += 1
            evenement.save()
            resultat["maj"][str(evenement.pk)] = evenement.version
            a_verifier.append(evenement)
            nouveau = Description_evenement(evenement, categories, arbre)
            historique.append({"titre": "Modification d'un évènement", "detail": nouveau, "old": ancien if ancien != nouveau else None, "collaborateur_id": evenement.collaborateur_id,
                               "objet": "Evènement", "idobjet": evenement.pk, "classe": "EvenementCollaborateur", "utilisateur": user})
            if ancien_collaborateur != evenement.collaborateur_id:
                historique.append({"titre": "Transfert d'un évènement vers un autre collaborateur", "detail": ancien, "collaborateur_id": ancien_collaborateur,
                                   "objet": "Evènement", "idobjet": evenement.pk, "classe": "EvenementCollaborateur", "utilisateur": user})
        else:
            raise Erreur_enregistrement("Opération inconnue")

    if conflits:
        return {"conflits": conflits}

    # Vérification des chevauchements une fois toutes les opérations appliquées
    erreurs = Verifier_chevauchements([evenement for evenement in a_verifier if evenement.pk not in resultat["supprimes"]], categories)
    if erreurs:
        raise Erreur_enregistrement(erreurs[0]["message"])

    utils_historique.Ajouter_plusieurs(historique)
    return resultat


# ------------------------------------------------- Créations par lot (modèles, copie) -------------------------------------------------

def Creer_par_lot(nouveaux=[], collaborateurs=[], dates=[], conflit="ignorer", apercu=False, user=None, libelle=""):
    """ Crée une liste d'évènements (non enregistrés) en gérant les conflits.
        conflit : 'ignorer' (ne crée pas les évènements en conflit), 'remplacer' (supprime les évènements existants en conflit),
                  'effacer' (vide d'abord les dates concernées pour les collaborateurs) """
    ids_modifiables = Get_ids_modifiables(user)
    collaborateurs = [idcollaborateur for idcollaborateur in collaborateurs if idcollaborateur in ids_modifiables]
    nouveaux = [evenement for evenement in nouveaux if evenement.collaborateur_id in collaborateurs]
    categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
    arbre = Arbre()

    # Evènements existants
    existants = {}
    if dates:
        for evenement in Get_evenements(min(dates), max(dates), collaborateurs):
            existants.setdefault(evenement.collaborateur_id, []).append(evenement)

    a_supprimer = {}
    if conflit == "effacer":
        dates_set = set(dates)
        for idcollaborateur, liste in existants.items():
            for evenement in liste:
                if evenement.date_debut.date() in dates_set:
                    a_supprimer[evenement.pk] = evenement
        existants = {idcollaborateur: [evenement for evenement in liste if evenement.pk not in a_supprimer] for idcollaborateur, liste in existants.items()}

    def Chevauche(a, b):
        return a.date_debut < b.date_fin and a.date_fin > b.date_debut and not categories[a.type_evenement_id].chevauchement_possible \
               and not categories[b.type_evenement_id].chevauchement_possible

    valides, ignores = [], []
    for nouveau in nouveaux:
        if nouveau.type_evenement_id not in categories:
            ignores.append(nouveau)
            continue
        en_conflit = [evenement for evenement in existants.get(nouveau.collaborateur_id, []) if evenement.pk not in a_supprimer and Chevauche(nouveau, evenement)]
        if any(Chevauche(nouveau, autre) for autre in valides if autre.collaborateur_id == nouveau.collaborateur_id):
            ignores.append(nouveau)
            continue
        if en_conflit:
            if conflit == "remplacer":
                for evenement in en_conflit:
                    a_supprimer[evenement.pk] = evenement
            else:
                ignores.append(nouveau)
                continue
        valides.append(nouveau)

    resultat = {"nbre_crees": len(valides), "nbre_ignores": len(ignores), "nbre_supprimes": len(a_supprimer), "crees": [], "supprimes": []}
    if apercu:
        return resultat

    # Enregistrement
    resultat["supprimes"] = [Serialiser_evenement(evenement) for evenement in a_supprimer.values()]
    historique = []
    for evenement in a_supprimer.values():
        historique.append({"titre": "Suppression d'un évènement (%s)" % libelle, "detail": Description_evenement(evenement, categories, arbre), "collaborateur_id": evenement.collaborateur_id,
                           "objet": "Evènement", "idobjet": evenement.pk, "classe": "EvenementCollaborateur", "utilisateur": user})
    EvenementCollaborateur.objects.filter(pk__in=list(a_supprimer.keys())).delete()
    for evenement in valides:
        evenement.version = 1
        evenement.save()
        historique.append({"titre": "Ajout d'un évènement (%s)" % libelle, "detail": Description_evenement(evenement, categories, arbre), "collaborateur_id": evenement.collaborateur_id,
                           "objet": "Evènement", "idobjet": evenement.pk, "classe": "EvenementCollaborateur", "utilisateur": user})
    resultat["crees"] = [Serialiser_evenement(evenement) for evenement in valides]
    utils_historique.Ajouter_plusieurs(historique)
    return resultat


def Generer_depuis_modeles(modeles=[], collaborateurs=[], dates=[]):
    """ Evènements (non enregistrés) issus de modèles de planning, en respectant fériés, périodes et contrats """
    from core.models import LigneModelePlanningCollaborateur
    from collaborateurs.utils.utils_evenements import Is_evenement_in_contrat
    liste_vacances = list(Vacance.objects.all())
    liste_feries = list(Ferie.objects.all())
    contrats = {}
    for contrat in ContratCollaborateur.objects.filter(collaborateur_id__in=collaborateurs):
        contrats.setdefault(contrat.collaborateur_id, []).append(contrat)
    lignes = list(LigneModelePlanningCollaborateur.objects.select_related("modele").filter(modele__in=modeles))

    nouveaux, hors_contrat = [], 0
    for date in sorted(set(dates)):
        est_ferie = utils_dates.EstFerie(date, liste_feries)
        est_vacances = utils_dates.EstEnVacances(date=date, liste_vacances=liste_vacances)
        for ligne in lignes:
            if ligne.jour != date.weekday():
                continue
            if est_ferie and not ligne.modele.inclure_feries:
                continue
            if (ligne.periode == "SCOLAIRES" and est_vacances) or (ligne.periode == "VACANCES" and not est_vacances):
                continue
            date_fin = datetime.datetime.combine(date, ligne.heure_fin)
            if ligne.heure_fin <= ligne.heure_debut:
                date_fin += datetime.timedelta(days=1)
            for idcollaborateur in collaborateurs:
                evenement = EvenementCollaborateur(collaborateur_id=idcollaborateur, type_evenement_id=ligne.type_evenement_id, titre=ligne.titre,
                                                   affectation_id=ligne.affectation_id, date_debut=datetime.datetime.combine(date, ligne.heure_debut), date_fin=date_fin)
                if not Is_evenement_in_contrat(evenement=evenement, contrats=contrats.get(idcollaborateur, [])):
                    hors_contrat += 1
                    continue
                nouveaux.append(evenement)
    return nouveaux, hors_contrat


def Generer_copie(source_debut=None, source_fin=None, destination_debut=None, collaborateurs=[]):
    """ Evènements (non enregistrés) copiés d'une période vers une autre """
    decalage = destination_debut - source_debut
    nouveaux = []
    for evenement in Get_evenements(source_debut, source_fin, collaborateurs):
        if not (source_debut <= evenement.date_debut.date() <= source_fin):
            continue
        nouveaux.append(EvenementCollaborateur(collaborateur_id=evenement.collaborateur_id, type_evenement_id=evenement.type_evenement_id, titre=evenement.titre,
                                               affectation_id=evenement.affectation_id, date_debut=evenement.date_debut + decalage, date_fin=evenement.date_fin + decalage))
    dates_destination = [source_debut + decalage + datetime.timedelta(days=n) for n in range((source_fin - source_debut).days + 1)]
    return nouveaux, dates_destination


# ------------------------------------------------- Calculs de temps -------------------------------------------------

def Duree_comptabilisee(evenement=None, categorie=None, realise=False):
    """ Durée en minutes comptabilisée dans le temps de travail (négative pour les catégories soustraites) """
    debut, fin = (evenement.realise_debut, evenement.realise_fin) if realise else (evenement.date_debut, evenement.date_fin)
    if not debut or not fin or not categorie:
        return 0
    minutes = (fin - debut).total_seconds() / 60
    if categorie.type == "ADDITION":
        return minutes
    if categorie.type == "SOUSTRACTION":
        return -minutes
    return 0


def Minutes_dans_plage(debut=None, fin=None, plage_debut=None, plage_fin=None):
    """ Minutes de [debut, fin] comprises dans la plage horaire quotidienne [plage_debut, plage_fin[ (en heures, plage pouvant passer minuit) """
    total = 0
    jour = debut.date() - datetime.timedelta(days=1)
    while jour <= fin.date():
        for a, b in ([(plage_debut, plage_fin)] if plage_debut < plage_fin else [(plage_debut, 24), (0, plage_fin)]):
            p_debut = datetime.datetime.combine(jour, datetime.time(0)) + datetime.timedelta(hours=a)
            p_fin = datetime.datetime.combine(jour, datetime.time(0)) + datetime.timedelta(hours=b)
            chevauchement = (min(fin, p_fin) - max(debut, p_debut)).total_seconds() / 60
            if chevauchement > 0:
                total += chevauchement
        jour += datetime.timedelta(days=1)
    return total


def Heures_attendues(contrats=[], dates=[], liste_feries=[]):
    """ Heures attendues par le contrat sur une liste de dates : volume hebdomadaire / 5 par jour ouvré (lundi-vendredi, hors fériés) """
    total = 0.0
    for date in dates:
        if date.weekday() >= 5 or utils_dates.EstFerie(date, liste_feries):
            continue
        for contrat in contrats:
            if contrat.heures_hebdo and contrat.date_debut <= date and (not contrat.date_fin or date <= contrat.date_fin):
                total += float(contrat.heures_hebdo) / 5 * 60
                break
    return total


def Format_minutes(minutes=0):
    signe = "-" if minutes < 0 else ""
    minutes = int(round(abs(minutes)))
    return "%s%dh%02d" % (signe, minutes // 60, minutes % 60)


# ------------------------------------------------- Remplissage des affectations -------------------------------------------------

def Get_remplissages(date_debut=None, date_fin=None):
    """ Consommations prévues (réservations et présences) par date et par affectation, pour les affectations liées à une activité.
        Une affectation sans lien cumule les consommations de ses sous-affectations liées les plus proches.
        Renvoie {"AAAA-MM-JJ|idaffectation": [{"a": abrégé, "n": nom, "p": prévus, "c": places ou None, "s": seuil d'alerte}, ...]} """
    from django.db.models import Count
    from core.models import UniteRemplissage, Consommation, Remplissage, Ouverture

    arbre = Arbre()
    liees = [affectation for affectation in arbre.affectations.values() if affectation.activite_id]
    if not liees:
        return {}
    activites = {affectation.activite_id for affectation in liees}

    # Unités de remplissage et unités de consommation associées
    unites_remplissage = {}
    unites_par_conso = {}
    for unite in UniteRemplissage.objects.prefetch_related("unites").filter(activite__in=activites).order_by("ordre"):
        unites_remplissage[unite.pk] = unite
        for unite_conso in unite.unites.all():
            unites_par_conso.setdefault(unite_conso.pk, []).append(unite.pk)
    unites_selectionnees = {}
    for affectation in liees:
        unites_selectionnees[affectation.pk] = list(affectation.unites_remplissage.values_list("pk", flat=True))

    # Consommations prévues : clé (date, unité de remplissage, groupe ou 0 pour le total)
    prevus = {}
    conditions = Q(activite__in=activites, date__gte=date_debut, date__lte=date_fin, etat__in=("reservation", "present"))
    for conso in Consommation.objects.filter(conditions).values("date", "unite", "groupe", "quantite").annotate(nbre=Count("pk")):
        quantite = conso["nbre"] * conso["quantite"] if conso["quantite"] else conso["nbre"]
        for idunite in unites_par_conso.get(conso["unite"], []):
            for idgroupe in {conso["groupe"] or 0, 0}:
                cle = (conso["date"], idunite, idgroupe)
                prevus[cle] = prevus.get(cle, 0) + quantite

    # Capacités
    capacites = {(remplissage.date, remplissage.unite_remplissage_id, remplissage.groupe_id or 0): remplissage.places
                 for remplissage in Remplissage.objects.filter(activite__in=activites, date__gte=date_debut, date__lte=date_fin)}

    # Ouvertures : (date, unité de remplissage, groupe ou 0)
    ouvertures = set()
    for ouverture in Ouverture.objects.filter(activite__in=activites, date__gte=date_debut, date__lte=date_fin).values("date", "unite", "groupe"):
        for idunite in unites_par_conso.get(ouverture["unite"], []):
            ouvertures.add((ouverture["date"], idunite, ouverture["groupe"] or 0))
            ouvertures.add((ouverture["date"], idunite, 0))

    def Calculer(affectation, date):
        idgroupe = affectation.groupe_id or 0
        resultats = []
        for idunite in unites_selectionnees[affectation.pk] or [pk for pk, unite in unites_remplissage.items() if unite.activite_id == affectation.activite_id]:
            unite = unites_remplissage.get(idunite)
            if not unite or (unite.date_debut and date < unite.date_debut) or (unite.date_fin and date > unite.date_fin):
                continue
            nbre = prevus.get((date, idunite, idgroupe), 0)
            if not nbre and (date, idunite, idgroupe) not in ouvertures:
                continue
            places = capacites.get((date, idunite, idgroupe))
            resultats.append({"a": unite.abrege, "n": unite.nom, "p": nbre, "c": places or None, "s": unite.seuil_alerte})
        return resultats

    # Calcul par date pour chaque affectation (directement liée ou cumul des sous-affectations)
    resultats = {}
    cache = {}
    nbre_jours = (date_fin - date_debut).days + 1
    for idaffectation in arbre.affectations:
        sources = arbre.Get_sources_remplissage(idaffectation)
        if not sources:
            continue
        for index in range(nbre_jours):
            date = date_debut + datetime.timedelta(days=index)
            fusion = []
            for source in sources:
                if (source.pk, date) not in cache:
                    cache[(source.pk, date)] = Calculer(source, date)
                for item in cache[(source.pk, date)]:
                    existant = next((x for x in fusion if x["a"] == item["a"]), None)
                    if not existant:
                        fusion.append(dict(item))
                    else:
                        existant["p"] += item["p"]
                        existant["c"] = existant["c"] + item["c"] if existant["c"] is not None and item["c"] is not None else None
            if fusion:
                resultats["%s|%d" % (date, idaffectation)] = fusion
    return resultats
