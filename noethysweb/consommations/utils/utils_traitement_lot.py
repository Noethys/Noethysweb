# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from core.models import Ferie, Vacance
from core.utils import utils_dates


def Calculer(request=None, parametres={}):
    date_debut = parametres["date_debut"]
    date_fin = parametres["date_fin"]

    # Vérification des données
    erreurs = []
    if not date_debut: erreurs.append("date de début")
    if not date_fin: erreurs.append("date de fin")
    if date_debut and date_fin and date_fin < date_debut: erreurs.append("date de début supérieure à la date de début")
    if not parametres["jours_scolaires"] and not parametres["jours_vacances"]: erreurs.append("jours")

    # Récupération des unités
    dict_unites = {}
    for key, valeur in request.POST.items():
        if key.startswith("unite_"):
            chaine = key.split("_")
            IDunite = int(chaine[1])
            if len(chaine) == 2:
                dict_unites.setdefault(IDunite, {})
            if len(chaine) == 3 and IDunite in dict_unites:
                option = chaine[2]
                if option == "debut":
                    option = "heure_debut"
                    if utils_dates.HeureStrEnTime(valeur) == datetime.time(0, 0):
                        erreurs.append("l'heure de début n'est pas valide")
                if option == "fin":
                    option = "heure_fin"
                    if utils_dates.HeureStrEnTime(valeur) == datetime.time(0, 0):
                        erreurs.append("l'heure de fin n'est pas valide")
                if option == "quantite":
                    try:
                        valeur = int(valeur)
                    except:
                        erreurs.append("La quantité n'est pas valide")
                dict_unites[IDunite][option] = valeur

    if not dict_unites:
        erreurs.append("unités")

    # Affichage des erreurs
    if erreurs:
        return {"erreur": "Les champs suivants ne sont pas valides : %s." % ", ".join(erreurs)}

    # Importation de données
    liste_vacances = Vacance.objects.filter(date_fin__gte=parametres["date_debut"], date_debut__lte=parametres["date_fin"])
    liste_feries = Ferie.objects.all()

    # Génération des dates
    listeDates = [date_debut,]
    tmp = date_debut
    while tmp < date_fin:
        tmp += datetime.timedelta(days=1)
        listeDates.append(tmp)

    semaines = int(parametres["frequence_type"])

    liste_dates_valides = []
    date = date_debut
    numSemaine = int(semaines)
    dateTemp = date
    for date in listeDates:

        # Vérifie période et jour
        valide = False
        if utils_dates.EstEnVacances(date, liste_vacances):
            if str(date.weekday()) in parametres["jours_vacances"]:
                valide = True
        else:
            if str(date.weekday()) in parametres["jours_scolaires"]:
                valide = True

        # Calcul le numéro de semaine
        if listeDates:
            if date.weekday() < dateTemp.weekday():
                numSemaine += 1

        # Fréquence semaines
        if semaines in (2, 3, 4):
            if numSemaine % semaines != 0:
                valide = False

        # Semaines paires et impaires
        if valide and semaines in (5, 6):
            numSemaineAnnee = date.isocalendar()[1]
            if numSemaineAnnee % 2 == 0 and semaines == 6:
                valide = False
            if numSemaineAnnee % 2 != 0 and semaines == 5:
                valide = False

        # Vérifie si férié
        if not parametres["inclure_feries"] and utils_dates.EstFerie(date, liste_feries):
            valide = False

        if valide:
            liste_dates_valides.append(date)

        dateTemp = date

    # Données renvoyées vers la page
    donnees = {
        "success": True,
        "action": parametres["action_type"],
        "dates": liste_dates_valides,
        "unites": dict_unites,
    }
    return donnees
