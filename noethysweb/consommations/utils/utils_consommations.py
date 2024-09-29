# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from core.models import LISTE_ETATS_CONSO
from dateutil import relativedelta, rrule, parser


def Get_label_etat(etat="reservation"):
    for code, label in LISTE_ETATS_CONSO:
        if code == etat:
            return label
    return ""

def Calcule_dates_forfait_credit_auto(parametres_tarif={}, date_conso=None):
    """ Calcule les dates d'un forfait crédit applicable """
    date_conso = parser.parse(date_conso).date()

    def Get_date(code=""):
        # Début
        if code == "PREC_LUNDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.MO(-1))
        if code == "PREC_MARDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.TU(-1))
        if code == "PREC_MERCREDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.WE(-1))
        if code == "PREC_JEUDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.TH(-1))
        if code == "PREC_VENDREDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.FR(-1))
        if code == "PREC_SAMEDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.SA(-1))
        if code == "PREC_DIMANCHE": return date_conso + relativedelta.relativedelta(weekday=relativedelta.SU(-1))
        if code == "PREC_SEMAINE_PREMIER_JOUR": return date_conso + relativedelta.relativedelta(weekday=relativedelta.MO(-1))
        if code == "PREC_MOIS_PREMIER_JOUR": return datetime.date(year=date_conso.year, month=date_conso.month, day=1)
        if code == "PREC_JOUR": return date_conso
        if code.startswith("PREC_JOUR_MOINS_"): return date_conso + relativedelta.relativedelta(days=-int(code.replace("PREC_JOUR_MOINS_", "")))
        if code.startswith("PREC_MOIS_"): return {d.month: d for d in list(rrule.rrule(rrule.MONTHLY, dtstart=date_conso + relativedelta.relativedelta(day=1, years=-1), count=12))}.get(int(code.replace("PREC_MOIS_", "")))

        # Fin
        if code == "SUIV_LUNDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.MO(1))
        if code == "SUIV_MARDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.TU(1))
        if code == "SUIV_MERCREDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.WE(1))
        if code == "SUIV_JEUDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.TH(1))
        if code == "SUIV_VENDREDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.FR(1))
        if code == "SUIV_SAMEDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.SA(1))
        if code == "SUIV_DIMANCHE": return date_conso + relativedelta.relativedelta(weekday=relativedelta.SU(1))
        if code == "SUIV_MOIS_DERNIER_JOUR": return relativedelta.relativedelta(day=1, months=+1, days=-1)
        if code == "SUIV_JOUR": return date_conso
        if code == "SUIV_SEMAINE_VENDREDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.MO(-1)) + relativedelta.relativedelta(weekday=relativedelta.FR(1))
        if code == "SUIV_SEMAINE_SAMEDI": return date_conso + relativedelta.relativedelta(weekday=relativedelta.MO(-1)) + relativedelta.relativedelta(weekday=relativedelta.SA(1))
        if code.startswith("SUIV_JOUR_PLUS_"): return date_conso + relativedelta.relativedelta(days=int(code.replace("SUIV_JOUR_PLUS_", "")))
        if code.startswith("SUIV_MOIS_"): return {d.month: d for d in list(rrule.rrule(rrule.MONTHLY, dtstart=date_conso, bymonthday=-1, count=12))}.get(int(code.replace("SUIV_MOIS_", "")))

        return None

    date_debut = Get_date(parametres_tarif["debut"])
    date_fin = Get_date(parametres_tarif["fin"])
    return date_debut, date_fin
