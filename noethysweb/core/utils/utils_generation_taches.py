# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from dateutil.rrule import rrulestr
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from core.models import Tache_recurrente, Tache, Vacance
from core.utils import utils_dates


def Generer_taches():
    logger.debug("Lancement de la génération des tâches...")
    today = datetime.date.today()

    # Importation des vacances
    liste_vacances = Vacance.objects.filter(date_fin__lte=today+datetime.timedelta(365), date_debut__gte=today-datetime.timedelta(365))

    # Importation des tâches récurrentes
    conditions = Q(date_debut__lte=today) & (Q(date_fin__isnull=True) | Q(date_fin__gte=today))
    liste_taches_recurrentes = Tache_recurrente.objects.filter(conditions).order_by("date_debut")

    # Analyse des tâches récurrentes
    for tache_recurrente in liste_taches_recurrentes:
        recurrence = tache_recurrente.recurrence

        # Calcule s'il faut créer une tâche
        creer = False
        if "VACANCES" in recurrence:
            parametres = {param.split("=")[0]: param.split("=")[1] for param in tache_recurrente.recurrence.split(";")}
            for vacance in liste_vacances:
                if parametres["INTERVAL"] == "0" or parametres["INTERVAL"] == vacance.nom:
                    if parametres["BASE"] == "FIRST" and vacance.date_debut == today: creer = vacance
                    if parametres["BASE"] == "LAST" and vacance.date_fin == today: creer = vacance
                    if parametres["BASE"] == "BEFORE_FIRST" and vacance.date_debut - datetime.timedelta(days=int(parametres["NBJOURS"])) == today: creer = vacance
                    if parametres["BASE"] == "AFTER_FIRST" and vacance.date_debut + datetime.timedelta(days=int(parametres["NBJOURS"])) == today: creer = vacance
                    if parametres["BASE"] == "BEFORE_LAST" and vacance.date_fin - datetime.timedelta(days=int(parametres["NBJOURS"])) == today: creer = vacance
                    if parametres["BASE"] == "AFTER_LAST" and vacance.date_fin + datetime.timedelta(days=int(parametres["NBJOURS"])) == today: creer = vacance
        else:
            valide = True
            if "VACS_IN" in recurrence and not utils_dates.EstEnVacances(date=today, liste_vacances=liste_vacances):
                valide = False
            if "VACS_OUT" in recurrence and utils_dates.EstEnVacances(date=today, liste_vacances=liste_vacances):
                valide = False
            if valide:
                recurrence = recurrence.replace(";OPTIONS=VACS_IN", "").replace(";OPTIONS=VACS_OUT", "")
                if list(rrulestr(recurrence).between(datetime.datetime(today.year, today.month, today.day, 0, 0, 0), datetime.datetime(today.year, today.month, today.day, 23, 59, 59), inc=True)):
                    creer = True

        # Création de la tâche
        if creer and not Tache.objects.filter(tache_recurrente=tache_recurrente, date=today):
            titre = tache_recurrente.titre
            titre = titre.replace("{DATE_COURTE}", utils_dates.ConvertDateToFR(today))
            titre = titre.replace("{DATE_LONGUE}", utils_dates.DateComplete(today))
            titre = titre.replace("{NOM_JOUR}", utils_dates.LISTE_JOURS[today.weekday()])
            titre = titre.replace("{MOIS}", utils_dates.LISTE_MOIS[today.month-1])
            titre = titre.replace("{MOIS_PRECEDENT}", utils_dates.LISTE_MOIS[(today + relativedelta(months=-1)).month - 1])
            titre = titre.replace("{MOIS_SUIVANT}", utils_dates.LISTE_MOIS[(today + relativedelta(months=+1)).month - 1])
            titre = titre.replace("{ANNEE}", str(today.year))
            titre = titre.replace("{ANNEE_PRECEDENTE}", str(today.year-1))
            titre = titre.replace("{ANNEE_SUIVANTE}", str(today.year+1))
            titre = titre.replace("{NOM_VACANCE}", "%s %s" % (creer.nom, creer.annee) if creer != True else "")
            logger.debug("Génération de la tâche %s." % titre)
            tache = Tache.objects.create(tache_recurrente=tache_recurrente, titre=titre, date=today,
                                         utilisateur=tache_recurrente.utilisateur, structure=tache_recurrente.structure)

    logger.debug("Fin de la procédure de génération des tâches.")
