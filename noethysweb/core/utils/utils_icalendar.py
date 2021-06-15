# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import icalendar
import urllib
import datetime


class Calendrier():
    def __init__(self, nomFichier=None, url=None):
        try :
            # Ouverture du calendrier
            if url != None :
                fichier = urllib.request.urlopen(url, timeout=5)
            if nomFichier != None :
                fichier = open(nomFichier, "rb")
            # Lecture du fichier
            self.cal = icalendar.Calendar.from_ical(fichier.read())
            fichier.close()
        except :
            self.cal = None

    def GetEvents(self):
        """ Parcours les Events """
        listeEvents = []
        for component in self.cal.walk():
            if component.name == "VEVENT" :
                description = self.RechercheElement(component, "DESCRIPTION", "texte")
                date_debut = self.RechercheElement(component, "DTSTART", "date")
                date_fin = self.RechercheElement(component, "DTEND", "date")
                listeEvents.append({"description" : description, "date_debut" : date_debut, "date_fin" : date_fin})
        return listeEvents
    
    def RechercheElement(self, component=None, nom="DTSTART", type="date"):
        """ Recherche un élément dans un Event """
        if nom in component :
            if type == "date" : return component.decoded(nom)
            if type == "texte" : return u"%s" % component[nom]
        else :
            return None
    
    def GetTitre(self):
        """ Récupère le titre du calendrier """
        try :
            titre = self.cal["X-WR-CALNAME"]
        except :
            titre = None
        return titre
    
    def GetVacances(self):
        """ Récupère les périodes de vacances """
        listeEvents = self.GetEvents() 
        listeResultats = []

        # Recherche les petites vacances
        listeCorrespondances = [
            ("hiver", "Février"),
            ("printemps", "Pâques"),
            ("Toussaint", "Toussaint"),
            ("Noël", "Noël"),
            ]

        for nomOriginal, nomFinal in listeCorrespondances :
            for dictEvent in listeEvents :
                if nomOriginal in dictEvent["description"] :
                    if dictEvent["date_debut"] != None and dictEvent["date_fin"] != None :
                        annee = dictEvent["date_debut"].year
                        date_debut = dictEvent["date_debut"]
                        date_fin = dictEvent["date_fin"] - datetime.timedelta(days=1)
                        listeResultats.append({"annee" : annee, "nom" : nomFinal, "date_debut" : date_debut, "date_fin" : date_fin})

        # Recherche les grandes vacances
        dictTemp = {}
        for dictEvent in listeEvents :
            if u"élèves" or u"été" in dictEvent["description"]:
                annee = dictEvent["date_debut"].year
                if (annee in dictTemp) == False :
                    dictTemp[annee] = {"date_debut" : None, "date_fin" : None}
                if u"été" in dictEvent["description"] :
                    dictTemp[annee]["date_debut"] = dictEvent["date_debut"] + datetime.timedelta(days=1)
                if u"élèves" in dictEvent["description"] :
                    dictTemp[annee]["date_fin"] = dictEvent["date_debut"] - datetime.timedelta(days=1)

        for annee, dictDates in dictTemp.items():
            if dictDates["date_debut"] != None and dictDates["date_fin"] != None :
                listeResultats.append({"annee" : annee, "nom" : "Eté", "date_debut" : dictDates["date_debut"], "date_fin" : dictDates["date_fin"]})

        # Tri par date de début
        listeResultats.sort(key=lambda x: x["date_debut"])

        return listeResultats