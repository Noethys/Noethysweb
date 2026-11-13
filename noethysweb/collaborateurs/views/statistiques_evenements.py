# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, base64, io, os, uuid
logger = logging.getLogger(__name__)
from django.conf import settings
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import EvenementCollaborateur, TypeEvenementCollaborateur, ContratCollaborateur, AjustementObjectifCollaborateur, Ferie
from core.utils import utils_dates
from core.utils.utils_impression import Impression
from collaborateurs.forms.statistiques_evenements import Formulaire
from collaborateurs.utils import utils_objectif
from collaborateurs.utils.utils_affectations import Arbre
from collaborateurs.utils.utils_planning import Get_evenements
from collaborateurs.views.planning_individuel import Collaborateurs_accessibles

PERMISSION = "core.statistiques_evenements_collaborateurs"
MOIS_ABREGES = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
TYPES = (("ADDITION", "Temps comptabilisé"), ("SOUSTRACTION", "Temps soustrait"), ("NEUTRE", "Temps non comptabilisé"))
LABELS_TYPES = dict(TYPES)
NBRE_CATEGORIES_AFFICHEES = 6
NBRE_AFFECTATIONS_AFFICHEES = 10
COULEUR_AUTRES = "#b8c2cc"


# ---------------------------------------- Utilitaires ----------------------------------------

def Format_nombre(valeur, decimales=0):
    return "{:,.{}f}".format(float(valeur or 0), decimales).replace(",", " ").replace(".", ",")


def Format_heures(minutes=0, signe=False):
    """ Durée exacte : 1 398h30 (signe + ou - si demandé) """
    if minutes is None:
        return "-"
    prefixe = "-" if minutes < 0 else ("+" if signe and minutes > 0 else "")
    minutes = int(round(abs(minutes)))
    return "%s%sh%02d" % (prefixe, Format_nombre(minutes // 60), minutes % 60)


def Format_heures_arrondies(minutes=0):
    """ Durée arrondie à l'heure pour les indicateurs : 9 860 h """
    return "%s h" % Format_nombre(round((minutes or 0) / 60.0))


def Pourcentage(valeur, total, decimales=0):
    if not total:
        return None
    valeur = 100.0 * float(valeur) / float(total)
    return round(valeur, decimales) if decimales else round(valeur)


def Heures(minutes=0):
    return round((minutes or 0) / 60.0, 1)


def Minutes(debut=None, fin=None, borne_debut=None, borne_fin=None):
    """ Minutes de [debut, fin] comprises dans [borne_debut, borne_fin[ (None si horaires incomplets) """
    if not debut or not fin:
        return None
    return max(0.0, (min(fin, borne_fin) - max(debut, borne_debut)).total_seconds() / 60)


def Get_liste_mois(date_debut=None, date_fin=None):
    liste_mois, annee, mois = [], date_debut.year, date_debut.month
    while (annee, mois) <= (date_fin.year, date_fin.month):
        liste_mois.append((annee, mois))
        mois += 1
        if mois > 12:
            annee, mois = annee + 1, 1
    return liste_mois


def Repartir_par_mois(debut=None, fin=None, borne_debut=None, borne_fin=None):
    """ Découpe [debut, fin] (limité aux bornes) en minutes par mois """
    debut, fin = max(debut, borne_debut), min(fin, borne_fin)
    resultat = {}
    while debut < fin:
        mois_suivant = datetime.datetime(debut.year + (debut.month == 12), debut.month % 12 + 1, 1)
        morceau = min(fin, mois_suivant)
        resultat[(debut.year, debut.month)] = resultat.get((debut.year, debut.month), 0) + (morceau - debut).total_seconds() / 60
        debut = morceau
    return resultat


def Regrouper(liste=[], nbre_max=6, label_autres="Autres"):
    """ Conserve les nbre_max premiers éléments (label, valeur, couleur) et regroupe les suivants """
    liste = sorted(liste, key=lambda x: -x[1])
    resultat = {"labels": [x[0] for x in liste[:nbre_max]], "valeurs": [x[1] for x in liste[:nbre_max]], "couleurs": [x[2] for x in liste[:nbre_max]]}
    if len(liste) > nbre_max:
        resultat["labels"].append(label_autres)
        resultat["valeurs"].append(round(sum([x[1] for x in liste[nbre_max:]]), 1))
        resultat["couleurs"].append(COULEUR_AUTRES)
    return resultat


def Est_absence(categorie=None):
    """ Absences : temps soustrait, ou temps non comptabilisé pris en compte dans l'objectif (congés, maladie...) """
    if not categorie:
        return False
    return categorie.type == "SOUSTRACTION" or (categorie.type == "NEUTRE" and categorie.temps_travail_objectif != "NON")


def Nouvelle_ligne(**kwargs):
    ligne = {"nbre": 0, "collaborateurs": set(), "planifie": 0.0, "realise": 0.0, "ecart": 0.0, "nbre_realises": 0, "absences": 0.0}
    ligne.update(kwargs)
    return ligne


# ---------------------------------------- Objectifs ----------------------------------------

def Get_type_periode(contrats=[], date=None, parametres={}):
    """ Même règle que utils_objectif.Type_periode_defaut, sans requête """
    en_cours = [contrat for contrat in contrats if contrat.date_debut <= date and (not contrat.date_fin or contrat.date_fin >= date)]
    contrat = (en_cours or contrats[-1:] or [None])[-1]
    if contrat and contrat.objectif_periode:
        return contrat.objectif_periode
    return parametres["periode"]


def Calculer_objectif(idcollaborateur=None, date_debut=None, date_fin=None, contrats=[], ajustements=[], evenements=[], categories={}, liste_feries=[], parametres={}):
    """ Objectif proratisé sur la période sélectionnée, selon les règles du planning individuel.
        L'objectif est calculé sur chaque période de référence (civile ou scolaire) qui chevauche la période,
        puis limité aux jours de la période (objectif à date de fin - objectif à la veille du début). """
    type_periode = Get_type_periode(contrats, date_fin, parametres)
    resultat = {"objectif": 0.0, "planifie": 0.0, "unite": None}
    for annee in range(utils_objectif.Annee_periode(date_debut, type_periode, parametres), utils_objectif.Annee_periode(date_fin, type_periode, parametres) + 1):
        periode = utils_objectif.Get_periode(annee, type_periode, parametres)
        debut, fin = max(date_debut, periode["debut"]), min(date_fin, periode["fin"])
        if debut > fin:
            continue
        ajustements_periode = [ajustement for ajustement in ajustements if periode["debut"] <= ajustement.date <= periode["fin"]]
        options = {"idcollaborateur": idcollaborateur, "periode": periode, "parametres": parametres, "contrats": contrats, "ajustements": ajustements_periode,
                   "categories": categories, "liste_feries": liste_feries}
        calcul = utils_objectif.Calcul_objectif(date_reference=fin, evenements=evenements, **options)
        if not calcul.a_objectif:
            continue
        if resultat["unite"] and resultat["unite"] != calcul.unite:
            return None  # Unités différentes selon les périodes : pas de comparaison possible
        objectif = calcul.objectif_a_date
        if debut > periode["debut"]:
            objectif -= utils_objectif.Calcul_objectif(date_reference=debut - datetime.timedelta(days=1), calculer_planifie=False, **options).objectif_a_date
        resultat["unite"] = calcul.unite
        resultat["objectif"] += objectif
        resultat["planifie"] += sum([valeur for jour, valeur in calcul.planifie_par_jour.items() if debut <= jour <= fin])
    if not resultat["unite"]:
        return None
    resultat["taux"] = Pourcentage(resultat["planifie"], resultat["objectif"]) if resultat["objectif"] > 0 else None
    resultat["objectif_str"] = utils_objectif.Format_valeur(resultat["objectif"], resultat["unite"])
    resultat["planifie_str"] = utils_objectif.Format_valeur(resultat["planifie"], resultat["unite"])
    return resultat


# ---------------------------------------- Calculs ----------------------------------------

def Get_collaborateurs(parametres={}, user=None):
    collaborateurs = Collaborateurs_accessibles(user)
    if parametres.get("groupes"):
        collaborateurs = collaborateurs.filter(groupes__in=parametres["groupes"]).distinct()
    return {collaborateur.pk: collaborateur for collaborateur in collaborateurs}


def Get_filtre_affectations(parametres={}, arbre=None):
    """ Affectations sélectionnées et leurs sous-affectations (None = toutes) """
    if not parametres.get("affectations"):
        return None
    resultat = set()
    for idaffectation in parametres["affectations"]:
        resultat.add(idaffectation)
        resultat.update(arbre.Get_descendants(idaffectation))
    return resultat


def Filtrer_evenements(evenements=[], parametres={}, filtre_affectations=None):
    idcategories = {categorie.pk for categorie in parametres["categories"]}
    return [evenement for evenement in evenements if evenement.type_evenement_id in idcategories
            and (filtre_affectations is None or evenement.affectation_id in filtre_affectations)]


def Get_horaires(evenement=None, realise=False, categorie=None):
    """ Horaires analysés : le réalisé ne concerne que le temps comptabilisé, les autres catégories (absences...) restent planifiées """
    if realise and categorie and categorie.type == "ADDITION":
        return evenement.realise_debut, evenement.realise_fin
    return evenement.date_debut, evenement.date_fin


def Get_data(parametres={}, user=None):
    date_debut, date_fin = [utils_dates.ConvertDateENGtoDate(x) for x in parametres["periode"].split(";")]
    comparer = parametres.get("comparer", False)
    realise = parametres.get("donnees") == "REALISE"
    maintenant = datetime.datetime.now().replace(second=0, microsecond=0)
    aujourdhui = maintenant.date()
    borne_debut = datetime.datetime.combine(date_debut, datetime.time(0))
    borne_fin = datetime.datetime.combine(date_fin + datetime.timedelta(days=1), datetime.time(0))

    # Période précédente de même durée et comparaison à date équivalente si la période est en cours
    duree = date_fin - date_debut
    fin_precedente = date_debut - datetime.timedelta(days=1)
    debut_precedente = fin_precedente - duree
    en_cours = date_debut <= aujourdhui < date_fin
    date_equivalente = aujourdhui - (date_debut - debut_precedente) if en_cours else fin_precedente

    categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
    arbre = Arbre()
    collaborateurs = Get_collaborateurs(parametres, user)
    filtre_affectations = Get_filtre_affectations(parametres, arbre)
    positions_affectations = {affectation.pk: index for index, (affectation, niveau) in enumerate(arbre.Parcourir())}

    data = {
        "comparer": comparer, "en_cours": en_cours, "realise": realise, "libelle_donnees": "réalisé" if realise else "planifié",
        "date_debut_str": utils_dates.ConvertDateToFR(date_debut), "date_fin_str": utils_dates.ConvertDateToFR(date_fin),
        "periode_str": "%s - %s" % (utils_dates.ConvertDateToFR(date_debut), utils_dates.ConvertDateToFR(date_fin)),
        "categories": ", ".join(sorted([categorie.nom for categorie in parametres["categories"]])),
        "affectations": ", ".join([arbre.Get_chemin(idaffectation) for idaffectation in parametres.get("affectations", [])]) or "Toutes",
        "groupes": ", ".join(sorted([groupe.nom for groupe in parametres.get("groupes", [])])) or "Tous",
    }

    # Tous les évènements de la période (pour les objectifs et le suivi) puis ceux qui correspondent aux paramètres
    evenements_periode = list(Get_evenements(date_debut, date_fin, list(collaborateurs.keys())))
    evenements = Filtrer_evenements(evenements_periode, parametres, filtre_affectations)

    # ------------------- Parcours unique des évènements -------------------
    liste_mois = Get_liste_mois(date_debut, date_fin)
    mois_par_type = {code: {mois: 0.0 for mois in liste_mois} for code, label in TYPES}
    totaux = {"travail_planifie": 0.0, "travail_realise": 0.0, "travail_termine": 0.0, "travail_termine_realise": 0.0, "absences": 0.0, "travail": 0.0, "ecart": 0.0}
    par_collaborateur, par_categorie, par_affectation = {}, {}, {}
    nbre_realise_non_saisi, collaborateurs_concernes = 0, set()

    for evenement in evenements:
        categorie = categories[evenement.type_evenement_id]
        minutes_planifiees = Minutes(evenement.date_debut, evenement.date_fin, borne_debut, borne_fin) or 0.0
        minutes_realisees = Minutes(evenement.realise_debut, evenement.realise_fin, borne_debut, borne_fin)
        minutes = minutes_realisees if realise and categorie.type == "ADDITION" else minutes_planifiees
        collaborateurs_concernes.add(evenement.collaborateur_id)
        termine = evenement.date_fin <= maintenant

        # Temps de travail et absences (selon les données analysées)
        if categorie.type == "ADDITION":
            totaux["travail_planifie"] += minutes_planifiees
            totaux["travail_realise"] += minutes_realisees or 0.0
            if termine:
                totaux["travail_termine"] += minutes_planifiees
                totaux["travail_termine_realise"] += minutes_realisees or 0.0
                if minutes_realisees is None:
                    nbre_realise_non_saisi += 1
            if minutes_realisees is not None:
                totaux["ecart"] += minutes_realisees - minutes_planifiees
        if minutes is not None:
            if categorie.type == "ADDITION":
                totaux["travail"] += minutes
            elif Est_absence(categorie):
                totaux["absences"] += minutes
            horaires = Get_horaires(evenement, realise, categorie)
            for mois, valeur in Repartir_par_mois(horaires[0], horaires[1], borne_debut, borne_fin).items():
                if mois in mois_par_type[categorie.type]:
                    mois_par_type[categorie.type][mois] += valeur

        # Lignes de détail
        cles = (
            (par_collaborateur, evenement.collaborateur_id, lambda: Nouvelle_ligne(label=collaborateurs[evenement.collaborateur_id].Get_nom(), id=evenement.collaborateur_id)),
            (par_categorie, categorie.pk, lambda: Nouvelle_ligne(label=categorie.nom, type=LABELS_TYPES.get(categorie.type, ""), couleur=categorie.couleur)),
            (par_affectation, evenement.affectation_id, lambda: Nouvelle_ligne(label=arbre.Get_chemin(evenement.affectation_id) if evenement.affectation_id else "Sans affectation",
                                                                               sans=not evenement.affectation_id, ordre=positions_affectations.get(evenement.affectation_id, 0))),
        )
        for dictionnaire, cle, creer in cles:
            if cle not in dictionnaire:
                dictionnaire[cle] = creer()
            ligne = dictionnaire[cle]
            ligne["nbre"] += 1
            ligne["collaborateurs"].add(evenement.collaborateur_id)
            # Collaborateurs : temps de travail et absences. Catégories et affectations : durée des évènements
            if dictionnaire is par_collaborateur:
                if categorie.type == "ADDITION":
                    ligne["planifie"] += minutes_planifiees
                    ligne["realise"] += minutes_realisees or 0.0
                    if minutes_realisees is not None:
                        ligne["ecart"] += minutes_realisees - minutes_planifiees
                        ligne["nbre_realises"] += 1
                elif Est_absence(categorie) and minutes is not None:
                    ligne["absences"] += minutes
            else:
                ligne["planifie"] += minutes_planifiees
                ligne["realise"] += minutes_realisees or 0.0
                if minutes_realisees is not None:
                    ligne["ecart"] += minutes_realisees - minutes_planifiees
                    ligne["nbre_realises"] += 1
                if minutes is not None:
                    ligne["valeur"] = ligne.get("valeur", 0.0) + minutes

    data["nbre_evenements"] = len(evenements)
    data["nbre_collaborateurs"] = len(collaborateurs_concernes)
    data["evenements_par_collaborateur"] = Format_nombre(len(evenements) / len(collaborateurs_concernes), 1) if collaborateurs_concernes else "0"
    data["travail"], data["absences"] = totaux["travail"], totaux["absences"]
    data["travail_planifie"], data["travail_realise"], data["ecart"] = totaux["travail_planifie"], totaux["travail_realise"], totaux["ecart"]
    data["taux_realisation"] = Pourcentage(totaux["travail_termine_realise"], totaux["travail_termine"]) if totaux["travail_termine"] else None
    data["taux_absences"] = Pourcentage(totaux["absences"], totaux["travail"] + totaux["absences"], 1) if totaux["travail"] + totaux["absences"] else None

    # ------------------- Comparaison avec la période précédente -------------------
    data["evolution_evenements"] = data["evolution_travail"] = None
    valeurs_precedentes = []
    if comparer:
        borne_debut_prec = datetime.datetime.combine(debut_precedente, datetime.time(0))
        borne_fin_prec = datetime.datetime.combine(fin_precedente + datetime.timedelta(days=1), datetime.time(0))
        limite = datetime.datetime.combine(aujourdhui + datetime.timedelta(days=1), datetime.time(0)) if en_cours else borne_fin
        limite_prec = datetime.datetime.combine(date_equivalente + datetime.timedelta(days=1), datetime.time(0))
        evenements_prec = Filtrer_evenements(Get_evenements(debut_precedente, fin_precedente, list(collaborateurs.keys())), parametres, filtre_affectations)

        def Totaux(liste=[], debut=None, fin=None):
            nbre, travail = 0, 0.0
            for evenement in liste:
                if evenement.date_debut >= fin:
                    continue
                nbre += 1
                horaires = Get_horaires(evenement, realise, categories[evenement.type_evenement_id])
                if categories[evenement.type_evenement_id].type == "ADDITION":
                    travail += Minutes(horaires[0], horaires[1], debut, fin) or 0.0
            return nbre, travail

        nbre, travail = Totaux(evenements, borne_debut, limite)
        nbre_prec, travail_prec = Totaux(evenements_prec, borne_debut_prec, limite_prec)
        data["evolution_evenements"] = Pourcentage(nbre - nbre_prec, nbre_prec) if nbre_prec else None
        data["evolution_travail"] = Pourcentage(travail - travail_prec, travail_prec) if travail_prec else None

        # Temps comptabilisé par mois de la période précédente (aligné sur les mois de la période)
        liste_mois_prec = Get_liste_mois(debut_precedente, fin_precedente)
        mois_prec = {mois: 0.0 for mois in liste_mois_prec}
        for evenement in evenements_prec:
            horaires = Get_horaires(evenement, realise, categories[evenement.type_evenement_id])
            if categories[evenement.type_evenement_id].type == "ADDITION" and horaires[0] and horaires[1]:
                for mois, valeur in Repartir_par_mois(horaires[0], horaires[1], borne_debut_prec, borne_fin_prec).items():
                    if mois in mois_prec:
                        mois_prec[mois] += valeur
        valeurs_precedentes = [Heures(mois_prec[mois]) for mois in liste_mois_prec][:len(liste_mois)]

    # ------------------- Suivi administratif -------------------
    data["suivi"] = {
        "en_cours": EvenementCollaborateur.objects.filter(collaborateur_id__in=list(collaborateurs.keys()), date_debut__lte=maintenant, date_fin__gt=maintenant).count(),
        "realise_non_saisi": nbre_realise_non_saisi,
        "sans_categorie": len([evenement for evenement in evenements_periode if not evenement.type_evenement_id]),
        "chevauchements": Compter_chevauchements(evenements_periode, categories),
    }

    # ------------------- Objectifs -------------------
    objectifs = Get_objectifs(list(par_collaborateur.keys()), date_debut, date_fin, evenements_periode, categories)

    # ------------------- Graphiques -------------------
    afficher_annee = len(liste_mois) > 12
    labels_mois = [("%s %s" % (MOIS_ABREGES[m - 1], str(a)[2:])) if afficher_annee else MOIS_ABREGES[m - 1] for a, m in liste_mois]
    graphe_mois = {"labels": labels_mois, "series": [{"label": label, "code": code, "valeurs": [Heures(mois_par_type[code][mois]) for mois in liste_mois]} for code, label in TYPES],
                   "valeurs_precedentes": valeurs_precedentes}
    graphe_mois["series"] = [serie for serie in graphe_mois["series"] if any(serie["valeurs"])]

    graphe_categories = Regrouper([(ligne["label"], Heures(ligne.get("valeur", 0)), ligne["couleur"]) for ligne in par_categorie.values() if ligne.get("valeur")], NBRE_CATEGORIES_AFFICHEES)
    lignes_affectations = sorted([ligne for ligne in par_affectation.values() if ligne.get("valeur")], key=lambda l: -l["valeur"])
    affichees = lignes_affectations[:NBRE_AFFECTATIONS_AFFICHEES]
    graphe_affectations = {"labels": [ligne["label"] for ligne in affichees], "valeurs": [Heures(ligne["valeur"]) for ligne in affichees],
                           "neutres": [ligne["label"] == "Sans affectation" for ligne in affichees]}
    if len(lignes_affectations) > NBRE_AFFECTATIONS_AFFICHEES:
        graphe_affectations["labels"].append("Autres affectations")
        graphe_affectations["valeurs"].append(Heures(sum([ligne["valeur"] for ligne in lignes_affectations[NBRE_AFFECTATIONS_AFFICHEES:]])))
        graphe_affectations["neutres"].append(True)
    data["graphes"] = {"mois": graphe_mois, "categories": graphe_categories, "affectations": graphe_affectations}

    # ------------------- Détail -------------------
    total_duree = sum([ligne["planifie"] for ligne in par_categorie.values()])
    for dictionnaire in (par_collaborateur, par_categorie, par_affectation):
        for ligne in dictionnaire.values():
            ligne["nbre_collaborateurs"] = len(ligne.pop("collaborateurs"))
            ligne["nbre_str"], ligne["nbre_collaborateurs_str"] = Format_nombre(ligne["nbre"]), Format_nombre(ligne["nbre_collaborateurs"])
            ligne["planifie_str"], ligne["realise_str"], ligne["absences_str"] = Format_heures(ligne["planifie"]), Format_heures(ligne["realise"]), Format_heures(ligne["absences"])
            ligne["ecart_str"] = Format_heures(ligne["ecart"], signe=True) if ligne["nbre_realises"] else "-"
            ligne["part"] = Pourcentage(ligne["planifie"], total_duree, 1) if dictionnaire is not par_collaborateur else None
            ligne["part_str"] = "%s %%" % Format_nombre(ligne["part"], 1) if ligne["part"] is not None else "-"
    for idcollaborateur, ligne in par_collaborateur.items():
        ligne["objectif"] = objectifs.get(idcollaborateur)

    data["lignes"] = {
        "collaborateurs": sorted(par_collaborateur.values(), key=lambda l: l["label"]),
        "categories": sorted(par_categorie.values(), key=lambda l: l["label"]),
        "affectations": sorted(par_affectation.values(), key=lambda l: (l["sans"], l["ordre"])),
    }

    # Totaux du détail
    objectifs_heures = [objectif for objectif in objectifs.values() if objectif and objectif["unite"] == "heures"]
    total_objectif = sum([objectif["objectif"] for objectif in objectifs_heures])
    total_planifie_objectif = sum([objectif["planifie"] for objectif in objectifs_heures])
    data["total"] = {
        "nbre_str": Format_nombre(len(evenements)), "nbre_collaborateurs_str": Format_nombre(len(collaborateurs_concernes)),
        "travail_planifie_str": Format_heures(totaux["travail_planifie"]), "travail_realise_str": Format_heures(totaux["travail_realise"]),
        "ecart_str": Format_heures(totaux["ecart"], signe=True) if any([ligne["nbre_realises"] for ligne in par_collaborateur.values()]) else "-",
        "absences_str": Format_heures(totaux["absences"]),
        "duree_str": Format_heures(total_duree), "realise_str": Format_heures(sum([ligne["realise"] for ligne in par_categorie.values()])),
        "ecart_duree_str": Format_heures(sum([ligne["ecart"] for ligne in par_categorie.values()]), signe=True) if any([ligne["nbre_realises"] for ligne in par_categorie.values()]) else "-",
        "objectif_taux": Pourcentage(total_planifie_objectif, total_objectif) if total_objectif > 0 else None,
        "objectif_str": utils_objectif.Format_valeur(total_objectif), "objectif_planifie_str": utils_objectif.Format_valeur(total_planifie_objectif),
    }

    # Valeurs formatées
    data["nbre_evenements_str"] = Format_nombre(data["nbre_evenements"])
    data["nbre_collaborateurs_str"] = Format_nombre(data["nbre_collaborateurs"])
    data["travail_str"], data["absences_str"] = Format_heures_arrondies(data["travail"]), Format_heures_arrondies(data["absences"])
    data["travail_planifie_str"], data["travail_realise_str"] = Format_heures_arrondies(data["travail_planifie"]), Format_heures_arrondies(data["travail_realise"])
    data["ecart_str"] = Format_heures(data["ecart"], signe=True)
    data["taux_absences_str"] = Format_nombre(data["taux_absences"], 1) if data["taux_absences"] is not None else None
    return data


def Compter_chevauchements(evenements=[], categories={}):
    """ Nombre d'évènements qui en chevauchent un autre du même collaborateur, hors catégories qui l'autorisent """
    par_collaborateur = {}
    for evenement in evenements:
        categorie = categories.get(evenement.type_evenement_id)
        if categorie and categorie.chevauchement_possible:
            continue
        par_collaborateur.setdefault(evenement.collaborateur_id, []).append(evenement)
    chevauchements = set()
    for liste in par_collaborateur.values():
        liste.sort(key=lambda e: (e.date_debut, e.date_fin))
        dernier = None  # Evènement déjà parcouru qui se termine le plus tard
        for evenement in liste:
            if dernier and evenement.date_debut < dernier.date_fin:
                chevauchements.update((evenement.pk, dernier.pk))
            if not dernier or evenement.date_fin > dernier.date_fin:
                dernier = evenement
    return len(chevauchements)


def Get_objectifs(idcollaborateurs=[], date_debut=None, date_fin=None, evenements=[], categories={}):
    """ Objectifs de temps de travail des collaborateurs sur la période (requêtes groupées) """
    if not idcollaborateurs:
        return {}
    parametres = utils_objectif.Get_parametres()
    liste_feries = list(Ferie.objects.all())
    contrats, ajustements, evenements_collaborateurs = {}, {}, {}
    for contrat in ContratCollaborateur.objects.select_related("type_poste").filter(collaborateur_id__in=idcollaborateurs).order_by("date_debut"):
        contrats.setdefault(contrat.collaborateur_id, []).append(contrat)
    debut_ajustements = datetime.date(date_debut.year - 1, 1, 1)
    for ajustement in AjustementObjectifCollaborateur.objects.filter(collaborateur_id__in=idcollaborateurs, date__gte=debut_ajustements, date__lte=datetime.date(date_fin.year + 1, 12, 31)).order_by("date", "pk"):
        ajustements.setdefault(ajustement.collaborateur_id, []).append(ajustement)
    for evenement in evenements:
        evenements_collaborateurs.setdefault(evenement.collaborateur_id, []).append(evenement)

    resultats = {}
    for idcollaborateur in idcollaborateurs:
        if not contrats.get(idcollaborateur):
            resultats[idcollaborateur] = None
            continue
        try:
            resultats[idcollaborateur] = Calculer_objectif(idcollaborateur=idcollaborateur, date_debut=date_debut, date_fin=date_fin, contrats=contrats[idcollaborateur],
                                                           ajustements=ajustements.get(idcollaborateur, []), evenements=evenements_collaborateurs.get(idcollaborateur, []),
                                                           categories=categories, liste_feries=liste_feries, parametres=parametres)
        except Exception:
            logger.exception("Calcul de l'objectif impossible pour le collaborateur ID%s" % idcollaborateur)
            resultats[idcollaborateur] = None
    return resultats


# ---------------------------------------- Exports ----------------------------------------

def Get_parametres(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return None
    return form.cleaned_data


def Texte_objectif(objectif=None):
    if not objectif or objectif["taux"] is None:
        return "-"
    return "%s %%" % objectif["taux"]


def Get_tableaux(data={}):
    """ Colonnes et lignes des trois niveaux de détail (pour les exports) """
    return [
        ("Détail par collaborateur", ("Collaborateur", "Évènements", "Temps planifié", "Temps réalisé", "Écart réalisé", "Absences", "Retenu / objectif", "Atteinte"),
         [(l["label"], l["nbre"], l["planifie_str"], l["realise_str"], l["ecart_str"], l["absences_str"],
           ("%s / %s" % (l["objectif"]["planifie_str"], l["objectif"]["objectif_str"])) if l["objectif"] else "-", Texte_objectif(l["objectif"])) for l in data["lignes"]["collaborateurs"]],
         ("Total", data["total"]["nbre_str"], data["total"]["travail_planifie_str"], data["total"]["travail_realise_str"], data["total"]["ecart_str"], data["total"]["absences_str"],
          "%s / %s" % (data["total"]["objectif_planifie_str"], data["total"]["objectif_str"]) if data["total"]["objectif_taux"] is not None else "-",
          "%s %%" % data["total"]["objectif_taux"] if data["total"]["objectif_taux"] is not None else "-")),
        ("Détail par catégorie", ("Catégorie", "Type", "Évènements", "Collaborateurs", "Durée planifiée", "Durée réalisée", "Écart réalisé", "Part"),
         [(l["label"], l["type"], l["nbre"], l["nbre_collaborateurs"], l["planifie_str"], l["realise_str"], l["ecart_str"], l["part_str"]) for l in data["lignes"]["categories"]],
         ("Total", "", data["total"]["nbre_str"], data["total"]["nbre_collaborateurs_str"], data["total"]["duree_str"], data["total"]["realise_str"], data["total"]["ecart_duree_str"], "100 %")),
        ("Détail par affectation", ("Affectation", "Évènements", "Collaborateurs", "Durée planifiée", "Durée réalisée", "Écart réalisé", "Part"),
         [(l["label"], l["nbre"], l["nbre_collaborateurs"], l["planifie_str"], l["realise_str"], l["ecart_str"], l["part_str"]) for l in data["lignes"]["affectations"]],
         ("Total", data["total"]["nbre_str"], data["total"]["nbre_collaborateurs_str"], data["total"]["duree_str"], data["total"]["realise_str"], data["total"]["ecart_duree_str"], "100 %")),
    ]


def Get_indicateurs(data={}):
    def Evolution(valeur):
        return " (%s%s %% vs période précédente)" % ("+" if valeur >= 0 else "", valeur) if data["comparer"] and valeur is not None else ""
    return [
        ("Évènements", "%s%s" % (data["nbre_evenements_str"], Evolution(data["evolution_evenements"]))),
        ("Collaborateurs concernés", "%s (%s évènements par collaborateur)" % (data["nbre_collaborateurs_str"], data["evenements_par_collaborateur"])),
        ("Temps de travail (%s)" % data["libelle_donnees"], "%s%s" % (data["travail_str"], Evolution(data["evolution_travail"]))),
        ("Temps de travail planifié / réalisé", "%s / %s (écart %s)" % (data["travail_planifie_str"], data["travail_realise_str"], data["ecart_str"])),
        ("Taux de réalisation", "%s %%" % data["taux_realisation"] if data["taux_realisation"] is not None else "-"),
        ("Absences", "%s (%s %% du temps total)" % (data["absences_str"], data["taux_absences_str"]) if data["taux_absences_str"] else data["absences_str"]),
    ]


def Get_suivi(data={}):
    return [
        ("Évènements en cours", data["suivi"]["en_cours"]),
        ("Réalisés non saisis", data["suivi"]["realise_non_saisi"]),
        ("Évènements sans catégorie", data["suivi"]["sans_categorie"]),
        ("Chevauchements", data["suivi"]["chevauchements"]),
    ]


def Exporter_excel(request):
    """ Export des statistiques au format Excel """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=401)
    parametres = Get_parametres(request)
    if not parametres:
        return JsonResponse({"erreur": "Les paramètres saisis ne sont pas valides"}, status=401)
    data = Get_data(parametres, request.user)

    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    os.makedirs(rep_destination, exist_ok=True)
    nom_fichier = "statistiques_evenements.xlsx"

    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    format_titre = classeur.add_format({"bold": True, "font_size": 14})
    format_entete = classeur.add_format({"bold": True, "bg_color": "#efefef", "border": 1})
    format_total = classeur.add_format({"bold": True, "bg_color": "#f8f9fa"})
    format_heures = classeur.add_format({"num_format": "#,##0.0"})

    def Ecrire_tableau(feuille, ligne, colonnes, lignes, formats={}, total=None):
        for num_colonne, label in enumerate(colonnes):
            feuille.write(ligne, num_colonne, label, format_entete)
        for valeurs in lignes:
            ligne += 1
            for num_colonne, valeur in enumerate(valeurs):
                feuille.write(ligne, num_colonne, valeur, formats.get(num_colonne))
        if total:
            ligne += 1
            for num_colonne, valeur in enumerate(total):
                feuille.write(ligne, num_colonne, valeur, format_total)
        return ligne + 2

    # Indicateurs et suivi
    feuille = classeur.add_worksheet("Indicateurs")
    feuille.set_column(0, 0, 40)
    feuille.set_column(1, 1, 50)
    feuille.write(0, 0, "Statistiques des évènements", format_titre)
    feuille.write(1, 0, "Période : %s" % data["periode_str"])
    feuille.write(2, 0, "Catégories : %s" % data["categories"])
    feuille.write(3, 0, "Affectations : %s - Groupes : %s" % (data["affectations"], data["groupes"]))
    ligne = Ecrire_tableau(feuille, 5, ("Indicateur", "Valeur"), Get_indicateurs(data))
    Ecrire_tableau(feuille, ligne, ("Suivi administratif", "Nombre"), Get_suivi(data))

    # Détail
    for titre, colonnes, lignes, total in Get_tableaux(data):
        feuille = classeur.add_worksheet(titre.replace("Détail par ", "Par ").capitalize()[:31])
        feuille.set_column(0, 0, 34)
        feuille.set_column(1, len(colonnes), 16)
        Ecrire_tableau(feuille, 0, colonnes, lignes, total=total)

    # Graphiques
    graphes = data["graphes"]
    feuille = classeur.add_worksheet("Par mois")
    feuille.set_column(0, len(graphes["mois"]["series"]) + 1, 22)
    colonnes = ["Mois"] + ["%s (h)" % serie["label"] for serie in graphes["mois"]["series"]]
    if data["comparer"]:
        colonnes.append("Comptabilisé période précédente (h)")
    lignes = []
    for index, label in enumerate(graphes["mois"]["labels"]):
        valeurs = [label] + [serie["valeurs"][index] for serie in graphes["mois"]["series"]]
        if data["comparer"]:
            precedentes = graphes["mois"]["valeurs_precedentes"]
            valeurs.append(precedentes[index] if index < len(precedentes) else "")
        lignes.append(valeurs)
    Ecrire_tableau(feuille, 0, colonnes, lignes, formats={index: format_heures for index in range(1, len(colonnes))})

    classeur.close()
    return JsonResponse({"nom_fichier": os.path.join(rep_temp, nom_fichier)})


def Generer_pdf(request):
    """ Export des statistiques au format PDF (avec les graphiques envoyés par la page) """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=401)
    parametres = Get_parametres(request)
    if not parametres:
        return JsonResponse({"erreur": "Les paramètres saisis ne sont pas valides"}, status=401)
    data = Get_data(parametres, request.user)

    images = {}
    for nom in ("mois", "categories", "affectations"):
        valeur = request.POST.get("graphique_%s" % nom, "")
        if valeur.startswith("data:image/png;base64,") and len(valeur) < 5000000:
            try:
                images[nom] = base64.b64decode(valeur.split(",", 1)[1])
            except Exception:
                logger.warning("Image du graphique '%s' invalide" % nom)

    impression = Impression_statistiques(titre="Statistiques des évènements", dict_donnees={"data": data, "images": images}, request=request)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


class Impression_statistiques(Impression):
    def Draw(self):
        from reportlab.platypus import Table, TableStyle, Spacer, Paragraph, Image, KeepTogether
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib import colors
        from core.utils import utils_polices

        data = self.dict_donnees["data"]
        images = self.dict_donnees["images"]
        largeur = self.taille_page[0] - 75
        self.doc.leftMargin = self.doc.rightMargin = (self.taille_page[0] - largeur) / 2.0
        bleu, gris = colors.HexColor("#3c8dbc"), colors.HexColor("#dee2e6")
        style_titre = ParagraphStyle("titre", fontName=utils_polices.FONT_BOLD, fontSize=11, textColor=bleu, spaceBefore=4, spaceAfter=4)
        style_texte = ParagraphStyle("texte", fontName=utils_polices.FONT_NORMAL, fontSize=8, leading=10)

        self.Insert_header(detail="Période : %s" % data["periode_str"])
        self.story.append(Paragraph("<b>Catégories :</b> %s<br/><b>Affectations :</b> %s - <b>Groupes de collaborateurs :</b> %s - <b>Données analysées :</b> %s" % (
            data["categories"], data["affectations"], data["groupes"], data["libelle_donnees"]), style_texte))
        self.story.append(Spacer(0, 6))

        # Indicateurs et suivi administratif
        indicateurs, suivi = Get_indicateurs(data), Get_suivi(data)
        suivi += [("", "")] * (len(indicateurs) - len(suivi))
        lignes = [(Paragraph("<b>%s</b>" % label, style_texte), Paragraph(valeur, style_texte), "", label_suivi, Format_nombre(valeur_suivi) if label_suivi else "")
                  for (label, valeur), (label_suivi, valeur_suivi) in zip(indicateurs, suivi)]
        lignes.insert(0, (Paragraph("Indicateurs clés", style_titre), "", "", Paragraph("Suivi administratif", style_titre), ""))
        tableau = Table(lignes, [130, largeur * 0.62 - 130, 12, largeur * 0.38 - 52, 40])
        tableau.setStyle(TableStyle([
            ("SPAN", (0, 0), (1, 0)), ("SPAN", (3, 0), (4, 0)),
            ("FONT", (3, 1), (3, -1), utils_polices.FONT_NORMAL, 8), ("FONT", (4, 1), (4, -1), utils_polices.FONT_BOLD, 8),
            ("ALIGN", (4, 1), (4, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 1), (1, -1), 0.25, gris), ("LINEBELOW", (3, 1), (4, len(Get_suivi(data))), 0.25, gris),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ]))
        self.story.append(tableau)
        self.story.append(Spacer(0, 6))

        # Graphiques
        titres = {"mois": "Heures par mois (%s)" % data["libelle_donnees"], "categories": "Répartition par catégorie", "affectations": "Heures par affectation"}
        largeur_image = (largeur - 10) / 2
        for paire in (("mois", "categories"), ("affectations",)):
            cellules = []
            for nom in paire:
                contenu = [Paragraph(titres[nom], style_titre)]
                if nom in images:
                    image = Image(io.BytesIO(images[nom]))
                    ratio = image.imageHeight / float(image.imageWidth)
                    hauteur = min(largeur_image * ratio, 150)
                    image.drawWidth, image.drawHeight = hauteur / ratio, hauteur
                    contenu.append(image)
                else:
                    contenu.append(Paragraph("Graphique non disponible", style_texte))
                cellules.append(contenu)
            if len(cellules) == 1:
                cellules.append("")
            tableau = Table([cellules], [largeur_image + 5, largeur_image + 5])
            tableau.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            self.story.append(tableau)

        # Tableaux de détail
        style_entete = ParagraphStyle("entete", fontName=utils_polices.FONT_BOLD, fontSize=7.5, leading=9, alignment=2)
        style_entete_gauche = ParagraphStyle("entete_gauche", parent=style_entete, alignment=0)
        style_cellule = ParagraphStyle("cellule", fontName=utils_polices.FONT_NORMAL, fontSize=7.5, leading=9)
        proportions = {
            "Détail par collaborateur": ((0.21, 0.09, 0.11, 0.11, 0.1, 0.1, 0.19, 0.09), 1),
            "Détail par catégorie": ((0.18, 0.18, 0.09, 0.11, 0.12, 0.12, 0.11, 0.09), 2),
            "Détail par affectation": ((0.3, 0.1, 0.12, 0.13, 0.13, 0.12, 0.1), 1),
        }
        for titre, colonnes, lignes, total in Get_tableaux(data):
            largeurs, nbre_textes = proportions[titre]
            abreviations = {"Évènements": "Évts", "Collaborateurs": "Collab."}
            entetes = [Paragraph(abreviations.get(label, label) if index else label, style_entete_gauche if index < nbre_textes else style_entete) for index, label in enumerate(colonnes)]
            contenu = [entetes]
            for ligne in lignes:
                contenu.append([Paragraph(str(valeur), style_cellule) if index < nbre_textes else str(valeur) for index, valeur in enumerate(ligne)])
            contenu.append(total)
            tableau = Table(contenu, [largeur * proportion for proportion in largeurs], repeatRows=1)
            tableau.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, -1), utils_polices.FONT_NORMAL, 7.5), ("FONT", (0, -1), (-1, -1), utils_polices.FONT_BOLD, 7.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")), ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f8f9fa")),
                ("ALIGN", (nbre_textes, 0), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), 0.25, gris), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            self.story.append(Spacer(0, 6))
            self.story.append(KeepTogether([Paragraph(titre, style_titre), tableau]))


# ---------------------------------------- Vue ----------------------------------------

class View(CustomView, TemplateView):
    menu_code = "statistiques_evenements_collaborateurs"
    template_name = "collaborateurs/statistiques_evenements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Statistiques des évènements"
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, data=Get_data(form.cleaned_data, request.user)))
