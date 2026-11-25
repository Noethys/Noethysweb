# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Taux d'encadrement heure par heure.

    Le calcul se fait par quart d'heure : un individu ou un collaborateur est présent sur un quart d'heure si le milieu
    de ce quart d'heure est compris dans sa plage horaire. Chaque heure affiche ensuite son pire quart d'heure.

    - Individus : individus distincts ayant une consommation réservée ou présente sur les unités de remplissage
      de l'affectation (ou de ses sous-affectations liées à une activité). Un individu n'est compté qu'une fois
      même s'il a plusieurs consommations au même moment. Horaires : ceux de la consommation, sinon ceux de l'unité
      de consommation, sinon ceux de l'unité de remplissage, sinon la plage par défaut (7h-19h).
    - Collaborateurs : collaborateurs ayant un évènement de temps comptabilisé sur l'affectation ou l'une de ses
      sous-affectations, hors évènements de temps soustrait (pauses...).
"""

import datetime, math
from django.db.models import Q
from collaborateurs.utils.utils_affectations import Arbre

DUREE_QUART = 15
NBRE_QUARTS = 24 * 60 // DUREE_QUART
PLAGE_DEFAUT = (7 * 60, 19 * 60)          # Plage retenue pour une consommation sans aucun horaire (en minutes)
SEUIL_ALERTE = 0.85                         # Même seuil que le widget de la page d'accueil


# ---------------------------------------- Fonctions de calcul (sans accès à la base) ----------------------------------------

def Minutes(heure=None):
    return heure.hour * 60 + heure.minute if heure else None


def Quarts(debut=0, fin=0):
    """ Quarts d'heure dont le milieu est compris dans [debut, fin[ (en minutes depuis minuit) """
    premier = max(0, math.ceil((debut - DUREE_QUART / 2) / DUREE_QUART))
    dernier = min(NBRE_QUARTS - 1, math.ceil((fin - DUREE_QUART / 2) / DUREE_QUART) - 1)
    return range(premier, dernier + 1)


def Etat(individus=0, collaborateurs=0, seuil=None):
    """ ko : dépassement ou aucun collaborateur, al : alerte, ok : conforme, None : aucun individu """
    if not individus:
        return None
    if not collaborateurs or individus / collaborateurs > seuil:
        return "ko"
    if individus / collaborateurs >= SEUIL_ALERTE * seuil:
        return "al"
    return "ok"


def Ratio(individus=0, collaborateurs=0):
    if not individus:
        return 0
    return individus / collaborateurs if collaborateurs else float("inf")


def Synthese_jour(individus_quarts={}, collaborateurs_quarts={}, seuil=None):
    """ individus_quarts et collaborateurs_quarts : {quart: nombre}. Renvoie la synthèse par heure et pour la journée, ou None sans individu """
    if not any(individus_quarts.values()):
        return None
    heures = []
    for heure in range(24):
        quarts = range(heure * 4, heure * 4 + 4)
        if not any(individus_quarts.get(q) or collaborateurs_quarts.get(q) for q in quarts):
            continue
        # Pire quart d'heure de l'heure (le plus grand nombre d'individus par collaborateur)
        avec_individus = [q for q in quarts if individus_quarts.get(q)]
        if avec_individus:
            pire = max(avec_individus, key=lambda q: (Ratio(individus_quarts.get(q, 0), collaborateurs_quarts.get(q, 0)), individus_quarts.get(q, 0)))
        else:
            pire = max(quarts, key=lambda q: collaborateurs_quarts.get(q, 0))
        individus, collaborateurs = individus_quarts.get(pire, 0), collaborateurs_quarts.get(pire, 0)
        heures.append({
            "h": heure, "e": individus, "c": collaborateurs, "cap": collaborateurs * seuil, "etat": Etat(individus, collaborateurs, seuil),
            "manque": max(0, math.ceil(individus / seuil) - collaborateurs) if individus else 0,
        })

    avec_individus = [heure for heure in heures if heure["e"]]
    pire = max(avec_individus, key=lambda heure: (Ratio(heure["e"], heure["c"]), heure["e"]))
    ratio = Ratio(pire["e"], pire["c"])
    return {
        "etat": pire["etat"], "taux": None if ratio == float("inf") else round(ratio, 1), "heure": pire["h"],
        "pic": max(individus_quarts.values()), "manque": max(heure["manque"] for heure in heures), "heures": heures,
    }


# ---------------------------------------- Chargement des données ----------------------------------------

def Get_lignes(arbre=None, idaffectation=None):
    """ Affectations à afficher dans l'ordre de l'arbre : celles qui ont un taux maximal (le leur ou hérité) et des consommations,
        précédées de leurs ancêtres en guise de titres. idaffectation : limite au sous-arbre de cette affectation. """
    lignes, retenues = [], set()
    perimetre = Descendants(arbre, idaffectation) if idaffectation else None
    for affectation, niveau in arbre.Parcourir():
        if perimetre is not None and affectation.pk not in perimetre:
            continue
        seuil = arbre.Get_seuil_encadrement(affectation.pk)
        calcul = bool(seuil and (affectation.seuil_encadrement or affectation.activite_id) and arbre.Get_sources_remplissage(affectation.pk))
        lignes.append({"affectation": affectation, "niveau": niveau, "seuil": seuil if calcul else None})
        if calcul:
            parent = affectation
            while parent:
                retenues.add(parent.pk)
                parent = arbre.affectations.get(parent.parent_id)
    return [ligne for ligne in lignes if ligne["affectation"].pk in retenues]


def Descendants(arbre=None, idaffectation=None):
    ids = {idaffectation}
    for enfant in arbre.enfants.get(idaffectation, []):
        ids |= Descendants(arbre, enfant.pk)
    return ids


def Charger_individus(date_debut=None, date_fin=None, arbre=None):
    """ {(idaffectation liée, date): {quart: set(idindividu)}} """
    from core.models import UniteRemplissage, Consommation

    liees = [affectation for affectation in arbre.affectations.values() if affectation.activite_id]
    if not liees:
        return {}
    activites = {affectation.activite_id for affectation in liees}

    # Unités de remplissage, unités de consommation associées et horaires de repli
    unites_remplissage, par_conso, horaires_unites = {}, {}, {}
    for unite in UniteRemplissage.objects.prefetch_related("unites").filter(activite__in=activites):
        unites_remplissage[unite.pk] = unite
        for unite_conso in unite.unites.all():
            par_conso.setdefault(unite_conso.pk, []).append(unite.pk)
            horaires_unites[unite_conso.pk] = (Minutes(unite_conso.heure_debut), Minutes(unite_conso.heure_fin))
    selection = {}
    for affectation in liees:
        ids = list(affectation.unites_remplissage.values_list("pk", flat=True))
        selection[affectation.pk] = set(ids or [pk for pk, unite in unites_remplissage.items() if unite.activite_id == affectation.activite_id])

    resultats = {}
    conditions = Q(activite__in=activites, date__gte=date_debut, date__lte=date_fin, etat__in=("reservation", "present"), individu__isnull=False)
    for conso in Consommation.objects.filter(conditions).values("date", "individu_id", "unite_id", "groupe_id", "activite_id", "heure_debut", "heure_fin"):
        ids_remplissage = par_conso.get(conso["unite_id"], [])
        if not ids_remplissage:
            continue
        for affectation in liees:
            if affectation.activite_id != conso["activite_id"] or (affectation.groupe_id and affectation.groupe_id != conso["groupe_id"]):
                continue
            unites = [unites_remplissage[pk] for pk in ids_remplissage if pk in selection[affectation.pk]
                      and not (unites_remplissage[pk].date_debut and conso["date"] < unites_remplissage[pk].date_debut)
                      and not (unites_remplissage[pk].date_fin and conso["date"] > unites_remplissage[pk].date_fin)]
            if not unites:
                continue
            # Horaires : consommation, sinon unité de consommation, sinon unité de remplissage, sinon plage par défaut
            debut, fin = Minutes(conso["heure_debut"]), Minutes(conso["heure_fin"])
            if debut is None or fin is None:
                debut, fin = horaires_unites.get(conso["unite_id"], (None, None))
            if debut is None or fin is None:
                debut, fin = Minutes(unites[0].heure_min), Minutes(unites[0].heure_max)
            if debut is None or fin is None or fin <= debut:
                debut, fin = PLAGE_DEFAUT
            quarts = resultats.setdefault((affectation.pk, conso["date"]), {})
            for quart in Quarts(debut, fin):
                quarts.setdefault(quart, set()).add(conso["individu_id"])
    return resultats


def Charger_collaborateurs(date_debut=None, date_fin=None):
    """ Présences ({(idaffectation, date): {quart: set(idcollaborateur)}}) et plages horaires
        ({(idaffectation, date, idcollaborateur): [(debut, fin)]}) des évènements de temps comptabilisé, pauses déduites """
    from collaborateurs.utils.utils_planning import Get_evenements

    presences, soustractions, plages = {}, {}, {}
    for evenement in Get_evenements(date_debut, date_fin).select_related("type_evenement"):
        if not evenement.type_evenement or evenement.type_evenement.type not in ("ADDITION", "SOUSTRACTION"):
            continue
        if evenement.type_evenement.type == "ADDITION" and not evenement.affectation_id:
            continue
        # Découpage par jour
        jour = max(evenement.date_debut.date(), date_debut)
        while jour <= min(evenement.date_fin.date(), date_fin):
            minuit = datetime.datetime.combine(jour, datetime.time(0, 0))
            debut = max(0, int((evenement.date_debut - minuit).total_seconds() // 60))
            fin = min(24 * 60, int((evenement.date_fin - minuit).total_seconds() // 60))
            if fin > debut:
                if evenement.type_evenement.type == "SOUSTRACTION":
                    soustractions.setdefault((evenement.collaborateur_id, jour), set()).update(Quarts(debut, fin))
                else:
                    quarts = presences.setdefault((evenement.affectation_id, jour), {})
                    for quart in Quarts(debut, fin):
                        quarts.setdefault(quart, set()).add(evenement.collaborateur_id)
                    plages.setdefault((evenement.affectation_id, jour, evenement.collaborateur_id), []).append((debut, fin))
            jour += datetime.timedelta(days=1)

    # Retrait des quarts d'heure de temps soustrait
    for (idaffectation, jour), quarts in presences.items():
        for quart, collaborateurs in quarts.items():
            collaborateurs -= {idcollaborateur for idcollaborateur in collaborateurs if quart in soustractions.get((idcollaborateur, jour), ())}
    return presences, plages


# ---------------------------------------- Calcul de la période ----------------------------------------

def Calculer(date_debut=None, date_fin=None, idaffectation=None):
    """ Synthèse de la période : lignes du tableau, cellules par date et indicateurs """
    arbre = Arbre()
    lignes = Get_lignes(arbre, idaffectation)
    dates = [date_debut + datetime.timedelta(days=index) for index in range((date_fin - date_debut).days + 1)]
    presences_individus = Charger_individus(date_debut, date_fin, arbre) if lignes else {}
    presences, plages = Charger_collaborateurs(date_debut, date_fin) if lignes else ({}, {})

    kpi = {"ko": 0, "al": 0, "ok": 0, "manque": 0}
    dates_avec_donnees = set()
    for ligne in lignes:
        ligne["cellules"] = {}
        if not ligne["seuil"]:
            continue
        affectation = ligne["affectation"]
        sources = [source.pk for source in arbre.Get_sources_remplissage(affectation.pk)]
        sous_arbre = Descendants(arbre, affectation.pk)
        for date in dates:
            # Individus distincts sur l'ensemble des sources, collaborateurs présents sur le sous-arbre
            individus = {}
            for idsource in sources:
                for quart, ids in presences_individus.get((idsource, date), {}).items():
                    individus.setdefault(quart, set()).update(ids)
            collaborateurs = {}
            for idaff in sous_arbre:
                for quart, ids in presences.get((idaff, date), {}).items():
                    collaborateurs.setdefault(quart, set()).update(ids)
            synthese = Synthese_jour({quart: len(ids) for quart, ids in individus.items()},
                                     {quart: len(ids) for quart, ids in collaborateurs.items()}, ligne["seuil"])
            if synthese:
                ligne["cellules"][date] = synthese
                dates_avec_donnees.add(date)
                kpi[synthese["etat"]] += 1
                kpi["manque"] += synthese["manque"]

    return {"date_debut": date_debut, "date_fin": date_fin, "dates": dates, "dates_avec_donnees": dates_avec_donnees,
            "lignes": lignes, "kpi": kpi, "arbre": arbre, "plages": plages}


def Format_taux(taux=None):
    """ 8 -> "1 / 8", 8.4 -> "1 / 8,4" (une décimale pour ne pas afficher 1 / 8 sur un dépassement de 8,4) """
    if taux is None:
        return "Aucun collaborateur"
    taux = round(taux, 1)
    return "1 / %s" % (str(int(taux)) if taux == int(taux) else str(taux).replace(".", ","))


def Format_heure(minutes=0):
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def Get_collaborateurs_jour(plages={}, arbre=None, idaffectation=None, date=None):
    """ Collaborateurs ayant du temps comptabilisé sur l'affectation (ou une sous-affectation) ce jour : {idcollaborateur: [(début, fin, idaffectation)]} """
    sous_arbre = Descendants(arbre, idaffectation)
    resultats = {}
    for (idaff, jour, idcollaborateur), liste in plages.items():
        if jour == date and idaff in sous_arbre:
            resultats.setdefault(idcollaborateur, []).extend((debut, fin, idaff) for debut, fin in liste)
    for liste in resultats.values():
        liste.sort()
    return resultats
