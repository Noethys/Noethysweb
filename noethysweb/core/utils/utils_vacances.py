# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import urllib.request, datetime, json, logging
from django.core.cache import cache
from core.utils import utils_dates

logger = logging.getLogger(__name__)

URL_CALENDRIER_SCOLAIRE = "https://www.data.gouv.fr/fr/datasets/r/000ae493-9fa8-4088-9f53-76d375204036"
CLE_CACHE = "calendrier_vacances_scolaires"
DUREE_CACHE = 60 * 60 * 24  # 24 heures
TIMEOUT = 20  # Doit rester sous le timeout des workers Gunicorn (30 s par défaut)


class Calendrier():
    def __init__(self, zone="A"):
        self.zone = zone
        self.erreur = None
        self.data = cache.get(CLE_CACHE)
        if self.data is None:
            self.data = self.Telecharger()

    def Telecharger(self):
        """ Télécharge le calendrier scolaire et le met en cache (uniquement en cas de succès) """
        try:
            with urllib.request.urlopen(URL_CALENDRIER_SCOLAIRE, timeout=TIMEOUT) as fichier:
                data = json.load(fichier)
        except Exception as err:
            logger.warning("Téléchargement du calendrier scolaire impossible : %s", err)
            self.erreur = str(err)
            return []
        if not isinstance(data, list) or not data:
            self.erreur = "Le fichier téléchargé ne contient aucune donnée exploitable."
            return []
        cache.set(CLE_CACHE, data, DUREE_CACHE)
        return data

    def GetVacances(self):
        liste_items = []
        for item in self.data:
            if item["zones"] == "Zone %s" % self.zone.upper() and "end_date" in item and "Enseignants" not in item.get("population", ""):
                description = item["description"]
                date_debut = utils_dates.ConvertDateENGtoDate(item["start_date"])
                if date_debut.weekday() != 5:
                    date_debut += datetime.timedelta(days=1)
                date_fin = utils_dates.ConvertDateENGtoDate(item["end_date"]) - datetime.timedelta(days=1)
                annee = date_debut.year

                if u"Hiver" in description: nom = u"Février"
                elif u"Printemps" in description: nom = u"Pâques"
                elif u"Été" in description: nom = u"Eté"
                elif u"Toussaint" in description: nom = u"Toussaint"
                elif u"Noël" in description: nom = u"Noël"
                else: nom = None

                periode = {"annee": annee, "nom": nom, "date_debut": date_debut, "date_fin": date_fin}
                if nom and periode not in liste_items and date_fin > date_debut:
                    liste_items.append(periode)

        # Tri par date de début
        liste_items.sort(key=lambda x: x["date_debut"])

        return liste_items
