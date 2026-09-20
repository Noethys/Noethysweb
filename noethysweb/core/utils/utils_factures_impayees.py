# -*- coding: utf-8 -*-
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.db.models import Q
from core.models import Facture, Activite, TypeGroupeActivite
from core.utils import utils_parametres

CATEGORIE = "factures_impayees"
STATUTS = ("retard", "echeance")
TRIS = ("echeance", "montant", "famille")
NB_MAX_LIGNES = 50

DEFAUT = {"statuts": list(STATUTS), "partiel": True, "groupes": [], "montant_min": "0", "jours_min": 0, "jours_max": 0, "tri": "echeance"}


def Nettoyer(brut):
    """ Valide et normalise les critères (ne fait jamais confiance aux données reçues) """
    brut = brut if isinstance(brut, dict) else {}
    try:
        montant_min = max(Decimal(str(brut.get("montant_min", 0)).replace(",", ".")), Decimal("0"))
    except (InvalidOperation, ValueError):
        montant_min = Decimal("0")
    try:
        jours_min = max(int(brut.get("jours_min", 0)), 0)
    except (TypeError, ValueError):
        jours_min = 0
    try:
        jours_max = max(int(brut.get("jours_max", 0)), 0)
    except (TypeError, ValueError):
        jours_max = 0
    tri = brut.get("tri")
    return {
        "statuts": [s for s in brut.get("statuts", DEFAUT["statuts"]) if s in STATUTS],
        "partiel": bool(brut.get("partiel", DEFAUT["partiel"])),
        "groupes": [int(x) for x in brut.get("groupes", []) if str(x).isdigit()],
        "montant_min": str(montant_min),
        "jours_min": jours_min,
        "jours_max": jours_max,
        "tri": tri if tri in TRIS else "echeance",
    }


def Get_criteres(request):
    valeur = utils_parametres.Get(nom="criteres", categorie=CATEGORIE, utilisateur=request.user, valeur={})
    return Nettoyer({**DEFAUT, **(valeur or {})})


def Set_criteres(request):
    """ Vue AJAX : mémorise les critères de l'utilisateur """
    try:
        criteres = Nettoyer(json.loads(request.POST.get("criteres", "{}")))
    except ValueError:
        return JsonResponse({"resultat": False}, status=400)
    if criteres["jours_max"] and criteres["jours_max"] < criteres["jours_min"]:
        return JsonResponse({"resultat": False, "erreur": "Le retard maximal doit être supérieur ou égal au retard minimum."}, status=400)
    utils_parametres.Set(nom="criteres", categorie=CATEGORIE, utilisateur=request.user, valeur=criteres)
    return JsonResponse({"resultat": True})


def Get_groupes(request):
    """ Groupes d'activités des structures de l'utilisateur """
    return TypeGroupeActivite.objects.filter(structure__in=request.user.structures.all()).order_by("nom")


def Get_donnees(request):
    """ Renvoie les factures impayées correspondant aux critères de l'utilisateur """
    today = datetime.date.today()
    c = Get_criteres(request)

    qs = Facture.objects.select_related("famille").exclude(etat="annulation").filter(
        solde_actuel__gte=max(Decimal(c["montant_min"]), Decimal("0.01")))

    # Statut (multi-sélection)
    q = Q()
    if "retard" in c["statuts"]:
        q |= Q(date_echeance__lt=today)
    if "echeance" in c["statuts"]:
        q |= Q(date_echeance__gte=today) | Q(date_echeance__isnull=True)
    qs = qs.filter(q) if c["statuts"] else qs.none()

    if c["jours_min"]:
        qs = qs.filter(date_echeance__lte=today - datetime.timedelta(days=c["jours_min"]))
    if c["jours_max"]:
        # Exclut les factures échues depuis plus de N jours (celles sans échéance ou pas encore échues restent)
        qs = qs.filter(Q(date_echeance__gte=today - datetime.timedelta(days=c["jours_max"])) | Q(date_echeance__isnull=True))
    if not c["partiel"]:
        qs = qs.exclude(regle__gt=0)

    # Groupes d'activités : on récupère les activités des groupes sélectionnés (limités aux structures
    # de l'utilisateur), puis on cherche leurs IDs dans Facture.activites (chaîne d'IDs séparés par ";", ex : "3;12")
    if c["groupes"]:
        groupes = Get_groupes(request).filter(pk__in=c["groupes"])
        ids_activites = set(Activite.objects.filter(groupes_activites__in=groupes).values_list("pk", flat=True))
        q = Q()
        for idactivite in ids_activites:
            q |= Q(activites__regex=r"(^|;)%d(;|$)" % idactivite)
        qs = qs.filter(q) if ids_activites else qs.none()

    qs = qs.order_by({"echeance": "date_echeance", "montant": "-solde_actuel", "famille": "famille__nom"}[c["tri"]], "numero")

    factures = list(qs)
    lignes = [{
        "facture": f,
        "restant": f.solde_actuel,
        "jours_retard": (today - f.date_echeance).days if f.date_echeance and f.date_echeance < today else 0,
        "partiel": bool(f.regle and f.regle > 0),
    } for f in factures]

    return {
        "factures_impayees_lignes": lignes[:NB_MAX_LIGNES],
        "factures_impayees_nb": len(lignes),
        "factures_impayees_nb_masquees": max(len(lignes) - NB_MAX_LIGNES, 0),
        "factures_impayees_total": sum((l["restant"] for l in lignes), Decimal("0")),
        "factures_impayees_criteres": c,
        "factures_impayees_criteres_json": json.dumps(c),
        "factures_impayees_nb_criteres": sum([
            set(c["statuts"]) != set(STATUTS), not c["partiel"], bool(c["groupes"]),
            Decimal(c["montant_min"]) > 0, c["jours_min"] > 0, c["jours_max"] > 0, c["tri"] != "echeance"]),
        "factures_impayees_groupes": Get_groupes(request),
    }
