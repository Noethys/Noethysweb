# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Contrôles de sécurité de la grille des consommations du portail famille.

Le navigateur n'est jamais cru :
- seules les inscriptions, consommations, prestations et mémos de la famille connectée sont acceptés ;
- les consommations existantes sont relues dans la base (seules les suppressions et les ajouts viennent du navigateur) ;
- les ajouts et suppressions respectent les dates modifiables, le délai de suppression, les unités visibles,
  les consommations pointées et le type de validation de l'activité ;
- à l'enregistrement, la facturation est recalculée par le serveur : les prestations, montants et aides
  envoyés par le navigateur sont ignorés.
"""

import logging, json, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.models import Inscription, Prestation, Consommation, Deduction, Evenement, MemoJournee
from portail.templatetags.planning import is_suppression_allowed

ETATS_POINTES = ("present", "absentj", "absenti")
ETATS_PORTAIL = ("reservation", "attente", "demande")


def _int(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def _date(valeur):
    try:
        return datetime.date.fromisoformat(str(valeur)[:10])
    except (TypeError, ValueError):
        return None


def _heure(valeur):
    """ Renvoie une heure au format HH:MM ou None """
    if not valeur:
        return None
    try:
        return datetime.datetime.strptime(str(valeur)[:5], "%H:%M").strftime("%H:%M")
    except ValueError:
        return None


def Prestation_to_dict(prestation, aides=[]):
    """ Même format que Get_generic_data() """
    from core.utils import utils_dates
    return {
        "date": str(prestation.date), "categorie": prestation.categorie, "label": prestation.label, "montant_initial": float(prestation.montant_initial),
        "montant": float(prestation.montant), "activite": prestation.activite_id, "tarif": prestation.tarif_id, "facture": prestation.facture_id,
        "famille": prestation.famille_id, "individu": prestation.individu_id, "categorie_tarif": prestation.categorie_tarif_id,
        "temps_facture": utils_dates.DeltaEnStr(prestation.temps_facture, separateur=":"),
        "quantite": prestation.quantite, "tarif_ligne": prestation.tarif_ligne_id, "tva": float(prestation.tva) if prestation.tva else None,
        "code_compta": prestation.code_compta, "aides": aides,
        "forfait_date_debut": str(prestation.forfait_date_debut) if prestation.forfait_date_debut else None,
        "forfait_date_fin": str(prestation.forfait_date_fin) if prestation.forfait_date_fin else None,
        "forfait": prestation.forfait, "dirty": False,
    }


def Get_prestations(conditions):
    """ Renvoie les prestations (depuis la base) au format de la grille """
    liste_prestations = list(Prestation.objects.filter(conditions))
    dict_aides = {}
    for deduction in Deduction.objects.filter(prestation__in=liste_prestations):
        dict_aides.setdefault(deduction.prestation_id, []).append({"label": deduction.label, "date": str(deduction.date), "aide": deduction.aide_id, "montant": float(deduction.montant)})
    return {str(prestation.pk): Prestation_to_dict(prestation, dict_aides.get(prestation.pk, [])) for prestation in liste_prestations}


def Get_dict_aides(prestations):
    """ Même format que get_donnees_for_facturation() de grille.js """
    return [{"idprestation": _int(idprestation) or idprestation, "famille": dict_prestation["famille"], "individu": dict_prestation["individu"],
             "date": dict_prestation["date"], "montant": dict_aide["montant"], "aide": dict_aide["aide"]}
            for idprestation, dict_prestation in prestations.items() for dict_aide in dict_prestation.get("aides", [])]


# ------------------------------------- Facturation (AJAX, affichage) -------------------------------------------

def Filtrer_donnees_facturation(request, donnees):
    """ Nettoie les données envoyées au calcul de facturation par le portail.
    Ce calcul ne sert qu'à l'affichage : l'enregistrement recalcule tout côté serveur. """
    famille = request.user.famille
    inscriptions = {inscription.pk: inscription for inscription in Inscription.objects.filter(famille=famille)}

    # Le mode pointeuse (qui enregistre directement) est interdit aux familles
    donnees["mode"] = "portail"

    # Cases touchées : uniquement les inscriptions de la famille, avec les valeurs de l'inscription (catégorie de tarif, groupe...)
    cases_touchees = {}
    for key_case, case in (donnees.get("cases_touchees") or {}).items():
        inscription = inscriptions.get(_int((case or {}).get("inscription")))
        if not inscription or not _date(case.get("date")):
            continue
        case.update({"inscription": inscription.pk, "famille": famille.pk, "individu": inscription.individu_id, "activite": inscription.activite_id,
                     "categorie_tarif": inscription.categorie_tarif_id, "groupe": inscription.groupe_id, "date": str(_date(case["date"]))})
        cases_touchees[key_case] = case
    donnees["cases_touchees"] = cases_touchees

    # Consommations : uniquement celles des inscriptions de la famille
    consommations = {}
    for liste in (donnees.get("consommations") or {}).values():
        for conso in (liste or []):
            if not isinstance(conso, dict):
                continue
            inscription = inscriptions.get(_int(conso.get("inscription")))
            if not inscription or not _date(conso.get("date")):
                continue
            conso.update({"famille": famille.pk, "individu": inscription.individu_id, "activite": inscription.activite_id, "date": str(_date(conso["date"]))})
            consommations.setdefault("%s_%s" % (conso["date"], inscription.pk), []).append(conso)
    donnees["consommations"] = consommations

    # Prestations : les existantes sont relues dans la base, les nouvelles (calculs précédents, non enregistrées) sont gardées pour l'affichage
    prestations_client = donnees.get("prestations") or {}
    prestations = Get_prestations(Q(pk__in=[_int(idprestation) for idprestation in prestations_client.keys() if _int(idprestation)]) & Q(famille=famille))
    for idprestation, dict_prestation in prestations_client.items():
        if "-" in str(idprestation) and isinstance(dict_prestation, dict) and dict_prestation.get("famille") == famille.pk:
            prestations[str(idprestation)] = dict_prestation
    donnees["prestations"] = prestations
    donnees["dict_aides"] = [dict_aide for dict_aide in (donnees.get("dict_aides") or []) if isinstance(dict_aide, dict) and dict_aide.get("famille") == famille.pk]

    # Suppressions : uniquement des ID de la famille
    suppressions = donnees.get("dict_suppressions") or {}
    donnees["dict_suppressions"] = {
        "consommations": list(Consommation.objects.filter(pk__in=[_int(pk) for pk in suppressions.get("consommations", []) if _int(pk)], inscription__famille=famille).values_list("pk", flat=True)),
        "prestations": [], "memos": [],
    }
    return donnees


# ------------------------------------- Enregistrement --------------------------------------------

def Securiser_donnees_save(request, donnees, data):
    """ Nettoie les données envoyées à Save_grille() par le planning du portail, puis recalcule la facturation côté serveur.
    data : résultat de planning.View.Get_data_planning() (inscriptions, dates, unités visibles...) """
    from consommations.views.grille import Facturation

    famille = request.user.famille
    activite = data["selection_activite"]
    inscriptions = {inscription.pk: inscription for inscription in data["liste_inscriptions"]}
    unites_visibles = {unite.pk for unite in data["liste_unites_visibles"]}
    dates_modifiables = {str(date) for date in data.get("dates_modifiables", [])}
    rejets = []

    # ------------------ Consommations ------------------
    liste_conso = [(key_case, conso) for key_case, liste in (donnees.get("consommations") or {}).items() for conso in (liste or []) if isinstance(conso, dict)]
    dict_db = {conso.pk: conso for conso in Consommation.objects.select_related("inscription").filter(
        pk__in=[_int(conso.get("pk")) for key_case, conso in liste_conso if _int(conso.get("pk"))], inscription__in=inscriptions.keys())}
    evenements_valides = set(Evenement.objects.filter(activite=activite).values_list("pk", flat=True))

    consommations = {}
    for key_case, conso in liste_conso:
        idconso = _int(conso.get("pk"))

        if idconso:
            # Consommation existante : tout est relu dans la base
            conso_db = dict_db.get(idconso)
            if not conso_db:
                rejets.append("conso %s" % conso.get("pk"))
                continue
            dict_conso = {
                "pk": conso_db.pk, "individu": conso_db.individu_id, "inscription": conso_db.inscription_id, "activite": conso_db.activite_id,
                "famille": conso_db.inscription.famille_id, "date": str(conso_db.date), "unite": conso_db.unite_id, "groupe": conso_db.groupe_id,
                "heure_debut": conso_db.heure_debut, "heure_fin": conso_db.heure_fin, "etat": conso_db.etat, "categorie_tarif": conso_db.categorie_tarif_id,
                "prestation": conso_db.prestation_id, "quantite": conso_db.quantite, "evenement": conso_db.evenement_id, "badgeage_debut": conso_db.badgeage_debut,
                "badgeage_fin": conso_db.badgeage_fin, "options": conso_db.options, "extra": conso_db.extra, "forfait": conso_db.forfait, "dirty": False,
            }

        else:
            # Nouvelle consommation : date modifiable, unité visible, inscription valide, état autorisé au portail
            inscription = inscriptions.get(_int(conso.get("inscription")))
            date = _date(conso.get("date"))
            idunite = _int(conso.get("unite"))
            idevenement = _int(conso.get("evenement"))
            etat = conso.get("etat")
            if not inscription or not date or str(date) not in dates_modifiables or idunite not in unites_visibles \
                    or (idevenement and idevenement not in evenements_valides) or etat not in ETATS_PORTAIL or not inscription.Is_inscription_in_periode(date, date):
                rejets.append("ajout conso %s %s %s" % (conso.get("date"), conso.get("unite"), etat))
                continue
            if activite.validation_type == "MANUELLE":
                etat = "demande"
            dict_conso = {
                "pk": str(conso.get("pk")), "individu": inscription.individu_id, "inscription": inscription.pk, "activite": inscription.activite_id,
                "famille": inscription.famille_id, "date": str(date), "unite": idunite, "groupe": inscription.groupe_id,
                "heure_debut": _heure(conso.get("heure_debut")), "heure_fin": _heure(conso.get("heure_fin")), "etat": etat,
                "categorie_tarif": inscription.categorie_tarif_id, "prestation": None,
                "quantite": max(1, min(_int(conso.get("quantite")) or 1, 99)), "evenement": idevenement, "badgeage_debut": None, "badgeage_fin": None,
                "options": conso.get("options") if isinstance(conso.get("options"), str) else None, "extra": None, "forfait": None, "dirty": True,
            }
            for cle in ("nom_evenement", "description_evenement"):
                if conso.get(cle):
                    dict_conso[cle] = str(conso[cle])

        dict_conso["key_case"] = key_case
        consommations.setdefault(key_case, []).append(dict_conso)

    # ------------------ Suppressions de consommations ------------------
    # De la famille, non pointées, hors forfait, dans le délai de suppression (ou demande en attente de validation)
    suppressions = donnees.get("suppressions") or {}
    liste_conso_suppr = []
    for conso in Consommation.objects.filter(pk__in=[_int(pk) for pk in suppressions.get("consommations", []) if _int(pk)], inscription__in=inscriptions.keys()):
        if conso.etat not in ETATS_POINTES and not conso.forfait and (conso.etat == "demande" or is_suppression_allowed(conso.date, data)):
            liste_conso_suppr.append(conso)
        else:
            rejets.append("suppression conso %d" % conso.pk)
    suppressions_conso = [conso.pk for conso in liste_conso_suppr]

    # Une conso supprimée ne peut pas être aussi dans la grille
    for key_case in list(consommations.keys()):
        consommations[key_case] = [dict_conso for dict_conso in consommations[key_case] if dict_conso["pk"] not in suppressions_conso]

    # ------------------ Facturation recalculée par le serveur ------------------
    # Lignes à recalculer : toutes les lignes affichées (comme tout_recalculer() du portail) + celles des conso de la grille et des suppressions
    lignes = {}
    for date in data.get("liste_dates", []):
        for inscription in inscriptions.values():
            if inscription.Is_inscription_in_periode(date, date):
                lignes.setdefault((str(date), inscription.pk), None)
    for liste in consommations.values():
        for dict_conso in liste:
            key_ligne = (dict_conso["date"], dict_conso["inscription"])
            if not lignes.get(key_ligne):
                lignes[key_ligne] = dict_conso["key_case"]
    for conso in liste_conso_suppr:
        lignes.setdefault((str(conso.date), conso.inscription_id), None)

    cases_touchees = {}
    for (date, idinscription), key_case in lignes.items():
        inscription = inscriptions[idinscription]
        cases_touchees[key_case or "ligne_%s_%s" % (date, idinscription)] = {
            "date": date, "inscription": inscription.pk, "activite": inscription.activite_id, "categorie_tarif": inscription.categorie_tarif_id,
            "famille": inscription.famille_id, "individu": inscription.individu_id, "groupe": inscription.groupe_id}

    consommations_facturation = {}
    for liste in consommations.values():
        for dict_conso in liste:
            dict_temp = dict(dict_conso, heure_debut=_heure(dict_conso["heure_debut"]), heure_fin=_heure(dict_conso["heure_fin"]))
            consommations_facturation.setdefault("%s_%s" % (dict_conso["date"], dict_conso["inscription"]), []).append(dict_temp)

    # Prestations existantes concernées (relues dans la base)
    dates = {date for date, idinscription in lignes.keys()}
    individus = {inscription.individu_id for inscription in inscriptions.values()}
    conditions = Q(famille=famille, activite=activite, individu_id__in=individus, categorie="consommation") & Q(date__in=dates)
    if dates:
        conditions |= Q(famille=famille, activite=activite, individu_id__in=individus, forfait_date_debut__lte=max(dates), forfait_date_fin__gte=min(dates))
    conditions |= Q(famille=famille, pk__in=[dict_conso["prestation"] for liste in consommations.values() for dict_conso in liste if dict_conso["prestation"]])
    prestations = Get_prestations(conditions)

    donnees_facturation = {
        "mode": "portail", "cases_touchees": cases_touchees, "consommations": consommations_facturation,
        "prestations": json.loads(json.dumps(prestations)), "dict_aides": Get_dict_aides(prestations),
        "liste_vacances": [(str(vacance.date_debut), str(vacance.date_fin)) for vacance in data.get("liste_vacances", [])],
        "dict_suppressions": {"consommations": suppressions_conso, "prestations": [], "memos": []},
    }
    retour = Facturation(donnees=donnees_facturation).Facturer()

    # Application du résultat
    prestations.update(retour["nouvelles_prestations"])
    suppressions_prestations = []
    for idprestation in retour["anciennes_prestations"]:
        prestations.pop(str(idprestation), None)
        if _int(idprestation):
            suppressions_prestations.append(_int(idprestation))
    suppressions_prestations = list(Prestation.objects.filter(pk__in=suppressions_prestations, famille=famille, facture__isnull=True).values_list("pk", flat=True))
    for liste in consommations.values():
        for dict_conso in liste:
            if dict_conso["key_case"] in retour["modifications_idprestation"]:
                idprestation = retour["modifications_idprestation"][dict_conso["key_case"]]
                if str(idprestation) != str(dict_conso["prestation"]):
                    dict_conso["prestation"] = idprestation
                    dict_conso["dirty"] = True

    # ------------------ Mémos : uniquement ceux des inscriptions de la page ------------------
    memos = {}
    ids_memos = set(MemoJournee.objects.filter(inscription__in=inscriptions.keys()).values_list("pk", flat=True))
    for key, dict_memo in (donnees.get("memos") or {}).items():
        if isinstance(dict_memo, dict) and _int(dict_memo.get("inscription")) in inscriptions and _date(dict_memo.get("date")) and (not dict_memo.get("pk") or _int(dict_memo.get("pk")) in ids_memos):
            memos[key] = {"pk": _int(dict_memo.get("pk")), "texte": str(dict_memo.get("texte") or ""), "inscription": _int(dict_memo["inscription"]),
                          "date": str(_date(dict_memo["date"])), "dirty": bool(dict_memo.get("dirty"))}
    suppressions_memos = [_int(pk) for pk in suppressions.get("memos", []) if _int(pk) in ids_memos]

    if rejets:
        logger.warning("Portail famille ID%d : données de la grille rejetées : %s" % (famille.pk, ", ".join(rejets[:50])))

    return {
        "activite": activite.pk,
        "consommations": consommations,
        "prestations": prestations,
        "memos": memos,
        "conso_masquees": {str(idconso): idprestation for idconso, idprestation in retour.get("modifications_conso_masquees", {}).items()},
        "suppressions": {"consommations": suppressions_conso, "prestations": suppressions_prestations, "memos": suppressions_memos},
    }
