# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Codes comptables et analytiques des prestations : contrôle avant export et modification par lot.

Le code retenu dans les exports est, par ordre de priorité : celui de la prestation, celui du type d'adhésion, celui de l'activité
(voir BaseExporter.Get_detail_factures). Une prestation est donc considérée sans code si aucun de ces trois niveaux n'en a.
"""

from django.db.models import Q
from core.models import Prestation, Facture
from core.utils import utils_dates

LONGUEUR_MAX_CODE = 200


def Nettoyer_code(valeur=None):
    """ Renvoie le code saisi sans espaces superflus, ou None s'il est vide """
    valeur = (valeur or "").strip()[:LONGUEUR_MAX_CODE]
    return valeur or None


def Condition_sans_code(champ="code_analytique"):
    """ Condition des prestations sans code effectif. champ : 'code_analytique' ou 'code_compta' """
    champ_parent = "code_comptable" if champ == "code_compta" else "code_analytique"
    conditions = Q()
    for chemin in (champ, "activite__%s" % champ_parent, "cotisation__type_cotisation__%s" % champ_parent):
        conditions &= Q(**{"%s__isnull" % chemin: True}) | Q(**{chemin: ""})
    return conditions


def Get_factures_periode(periode=""):
    """ Factures exportées pour la période 'AAAA-MM-JJ;AAAA-MM-JJ' (même sélection que les exports comptables) """
    date_debut, date_fin = [utils_dates.ConvertDateENGtoDate(date) for date in periode.split(";")]
    return Facture.objects.filter(date_edition__gte=date_debut, date_edition__lte=date_fin, etat__isnull=True)


def Get_anomalies(factures=None, champs=("code_analytique", "code_compta")):
    """ Renvoie les prestations des factures sans l'un des codes demandés, regroupées par label et activité :
    [{"key", "label", "idactivite", "activite", "nbre", "montant", "sans_code_analytique", "sans_code_compta"}] """
    prestations = Prestation.objects.filter(facture__in=factures)
    pks_sans_analytique = set(prestations.filter(Condition_sans_code("code_analytique")).values_list("pk", flat=True)) if "code_analytique" in champs else set()
    pks_sans_compta = set(prestations.filter(Condition_sans_code("code_compta")).values_list("pk", flat=True)) if "code_compta" in champs else set()
    if not pks_sans_analytique and not pks_sans_compta:
        return []

    dict_groupes = {}
    for pk, label, idactivite, nom_activite, montant in Prestation.objects.filter(pk__in=pks_sans_analytique | pks_sans_compta).values_list(
            "pk", "label", "activite_id", "activite__nom", "montant"):
        groupe = dict_groupes.setdefault((label, idactivite), {
            "key": "%s|%s" % (idactivite or 0, label), "label": label, "idactivite": idactivite, "activite": nom_activite or "",
            "nbre": 0, "montant": 0, "sans_code_analytique": 0, "sans_code_compta": 0})
        groupe["nbre"] += 1
        groupe["montant"] += montant
        if pk in pks_sans_analytique:
            groupe["sans_code_analytique"] += 1
        if pk in pks_sans_compta:
            groupe["sans_code_compta"] += 1
    return sorted(dict_groupes.values(), key=lambda groupe: (groupe["label"].lower(), groupe["activite"].lower()))


def Corriger_anomalies(factures=None, corrections=[], champs=("code_analytique", "code_compta")):
    """ Renseigne les codes manquants des prestations des factures.
    corrections : [{"label", "idactivite", "code_analytique", "code_compta"}]. Seules les prestations sans code effectif sont modifiées.
    Renvoie le nombre de prestations modifiées """
    pks_modifies = set()
    for correction in corrections:
        condition_groupe = Q(facture__in=factures, label=correction.get("label") or "")
        idactivite = correction.get("idactivite")
        condition_groupe &= Q(activite_id=int(idactivite)) if idactivite else Q(activite__isnull=True)
        for champ in champs:
            code = Nettoyer_code(correction.get(champ))
            if not code:
                continue
            prestations = Prestation.objects.filter(condition_groupe & Condition_sans_code(champ))
            pks = list(prestations.values_list("pk", flat=True))
            Prestation.objects.filter(pk__in=pks).update(**{champ: code})
            pks_modifies.update(pks)
    return len(pks_modifies)


def Modifier_codes(pks=[], code_analytique=None, effacer_code_analytique=False, code_compta=None, effacer_code_compta=False):
    """ Modification par lot des codes des prestations données. Un code vide n'est pas modifié, sauf si son effacement est demandé.
    Renvoie le nombre de prestations modifiées """
    modifications = {}
    for champ, code, effacer in (("code_analytique", code_analytique, effacer_code_analytique), ("code_compta", code_compta, effacer_code_compta)):
        if effacer:
            modifications[champ] = None
        elif Nettoyer_code(code):
            modifications[champ] = Nettoyer_code(code)
    if not modifications or not pks:
        return 0
    return Prestation.objects.filter(pk__in=pks).update(**modifications)
