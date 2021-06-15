# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from django.urls import reverse_lazy
from core.models import Unite, Ouverture, Groupe
from parametrage.views.activites import Onglet
from core.utils import utils_dates
import json


class View(Onglet, TemplateView):
    template_name = "parametrage/activite_calendrier.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        idactivite = kwargs.get("idactivite", None)
        context['box_titre'] = "Calendrier"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour définir les dates d'ouverture de l'activité."
        context['onglet_actif'] = "calendrier"
        context['boutons_liste'] = [
            {"label": "Modifier", "classe": "btn btn-success", "href": reverse_lazy("activites_ouvertures", args=[idactivite]), "icone": "fa fa-pencil"},
        ]
        liste_colonnes, liste_lignes = self.Get_ouvertures(idactivite=idactivite)
        context['liste_colonnes'] = liste_colonnes
        context['liste_lignes'] = json.dumps(liste_lignes)
        return context

    def Get_ouvertures(self, idactivite=None):
        # Préparation des colonnes
        liste_unites = Unite.objects.filter(activite_id=idactivite).order_by("ordre")
        liste_colonnes = ["Année/mois",] + [unite.abrege for unite in liste_unites]
        dict_colonnes = {unite.pk: index for index, unite in enumerate(liste_unites, start=1)}

        # Importation des ouvertures
        liste_ouvertures = Ouverture.objects.values("date", "unite").filter(activite_id=idactivite).distinct()

        # Analyse des ouvertures
        dict_ouvertures = {}
        dict_totaux = {}
        for ouverture in liste_ouvertures:
            annee = ouverture["date"].year
            mois = ouverture["date"].month
            idunite = ouverture["unite"]

            if annee not in dict_ouvertures:
                dict_ouvertures[annee] = {}
            if mois not in dict_ouvertures[annee]:
                dict_ouvertures[annee][mois] = {}
            if idunite not in dict_ouvertures[annee][mois]:
                dict_ouvertures[annee][mois][idunite] = 0
            dict_ouvertures[annee][mois][idunite] += 1

            if annee not in dict_totaux:
                dict_totaux[annee] = {}
            if idunite not in dict_totaux[annee]:
                dict_totaux[annee][idunite] = 0
            dict_totaux[annee][idunite] += 1

        # Création des lignes
        liste_lignes = []

        liste_annees = list(dict_ouvertures.keys())
        liste_annees.sort()
        for annee in liste_annees:
            idannee = "annee-%d" % annee
            ligne_annee = {"id": idannee, "pid": 0, "col0": str(annee), "regroupement": True}
            for idunite, nbre_dates in dict_totaux[annee].items():
                ligne_annee["col%d" % dict_colonnes[idunite]] = "%d date%s" % (nbre_dates, "s" if nbre_dates > 1 else "")
            liste_lignes.append(ligne_annee)

            liste_mois = list(dict_ouvertures[annee].keys())
            liste_mois.sort()
            for mois in liste_mois:
                ligne_mois = {"id": "mois-%d" % mois, "pid": idannee, "col0": utils_dates.LISTE_MOIS[mois-1].capitalize()}
                for idunite, nbre_dates in dict_ouvertures[annee][mois].items():
                    ligne_mois["col%d" % dict_colonnes[idunite]] = "%d date%s" % (nbre_dates, "s" if nbre_dates > 1 else "")
                liste_lignes.append(ligne_mois)

        return liste_colonnes, liste_lignes
