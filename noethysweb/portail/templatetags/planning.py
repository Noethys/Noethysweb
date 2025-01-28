# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.template.defaulttags import register
from core.utils import utils_dates
from dateutil import relativedelta


@register.filter
def rangelistfrom0(number):
    return range(number)


@register.filter
def rangelistfrom1(number):
    return range(1, number+1)


@register.filter
def is_modif_allowed(date, data):
    # Si le mode n'est pas portail on autorise les modifications
    if data["mode"] != "portail":
        return True

    # Mode consultation only pour le portail
    if "periode_reservation" in data:
        # Mode activé
        if data["periode_reservation"].mode_consultation and not data["periode_reservation"].mode_consultation_date:
            return False
        # Mode activé à partir d'une date donnée
        if data["periode_reservation"].mode_consultation and data["periode_reservation"].mode_consultation_date:
            if datetime.datetime.now() > data["periode_reservation"].mode_consultation_date:
                return False

    # On vérifie que la modification est autorisée sur cette date
    activite = data["selection_activite"]
    if activite.portail_reservations_limite:
        parametres_limite = activite.portail_reservations_limite.split("#")
        nbre_jours = int(parametres_limite[0])
        heure = datetime.datetime.strptime(parametres_limite[1], "%H:%M")

        jours_semaine = [relativedelta.MO, relativedelta.TU, relativedelta.WE, relativedelta.TH, relativedelta.FR, relativedelta.SA, relativedelta.SU]
        date_limite = datetime.datetime(year=date.year, month=date.month, day=date.day, hour=heure.hour, minute=heure.minute)

        # Jour J-x
        if 0 <= nbre_jours <= 999:
            x = 1
            while x <= nbre_jours:
                date_limite = date_limite - datetime.timedelta(days=1)
                date_valide = True

                # Vérifie que la date est hors week-end
                if "weekends" in activite.portail_reservations_limite and date_limite.weekday() in (5, 6):
                    date_valide = False

                # Vérifie que la date est hors fériés
                if "feries" in activite.portail_reservations_limite and utils_dates.EstFerie(date_limite, data["liste_feries"]):
                    date_valide = False

                # Vérifie que la date est hors jours exclus
                if "jours" in activite.portail_reservations_limite:
                    for chaine in activite.portail_reservations_limite.split("#"):
                        if "jours" in chaine:
                            for num_jour in [int(num_jour) for num_jour in chaine.replace("exclure_jours", "")]:
                                if date_limite.weekday() == num_jour:
                                    date_valide = False

                if date_valide == True:
                    x += 1

        # Lundi, mardi, mercredi... précédent
        if 1000 <= nbre_jours <= 1006:
            date_limite = date_limite - relativedelta.relativedelta(days=1, weekday=jours_semaine[nbre_jours - 1000](-1))

        # Lundi, mardi, mercredi... de la semaine précédente
        if 2000 <= nbre_jours <= 2006:
            date_limite = date_limite - relativedelta.relativedelta(
                weekday=relativedelta.SU(-1)) - relativedelta.relativedelta(weekday=jours_semaine[nbre_jours - 2000](-1))

        # Lundi, mardi, mercredi... de la semaine S-2
        if 3000 <= nbre_jours <= 3006:
            date_limite = date_limite - relativedelta.relativedelta(
                weekday=relativedelta.SU(-1)) - relativedelta.relativedelta(weekday=jours_semaine[nbre_jours - 3000](-2))

        # Validation de la date limite
        if datetime.datetime.now() > date_limite:
            return False

    return True
