# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from core.models import Unite, Ouverture, Groupe, Vacance, Ferie, Consommation
from core.utils import utils_dates
from parametrage.views.activites import Onglet


def Get_calendrier_annuel_ouvertures(request):
    """ Renvoie les jours du calendrier annuel des ouvertures """
    annee = int(request.POST.get("annee"))
    idactivite = int(request.POST.get("idactivite"))
    events = []

    # Périodes de vacances
    for vacance in Vacance.objects.filter(date_fin__gte=datetime.date(annee, 1, 1), date_debut__lte=datetime.date(annee, 12, 31)):
        events.append({
            "debut": [vacance.date_debut.year, vacance.date_debut.month-1, vacance.date_debut.day],
            "fin": [vacance.date_fin.year, vacance.date_fin.month-1, vacance.date_fin.day],
            "color": "#faffc9",
        })

    # Jours fériés
    for ferie in Ferie.objects.filter(Q(annee=annee) | Q(annee=0)):
        events.append({
            "debut": [annee, ferie.mois-1, ferie.jour],
            "fin": [annee, ferie.mois-1, ferie.jour],
            "color": "#eaeaea",
        })

    # Ouvertures
    consommations = [conso["date"] for conso in Consommation.objects.values("date").filter(activite_id=idactivite, date__gte=datetime.date(annee, 1, 1), date__lte=datetime.date(annee, 12, 31)).distinct()]
    for date in [ouverture["date"] for ouverture in Ouverture.objects.values("date").filter(activite_id=idactivite, date__gte=datetime.date(annee, 1, 1), date__lte=datetime.date(annee, 12, 31)).distinct().order_by("date")]:
        events.append({
            "debut": [date.year, date.month-1, date.day],
            "fin": [date.year, date.month-1, date.day],
            "ouvert": 1,
            "consommations": 1 if date in consommations else 0,
            "color": "#a5c3d4",
        })

    return JsonResponse(events, safe=False)


class View(Onglet, TemplateView):
    template_name = "parametrage/activite_calendrier.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        idactivite = kwargs.get("idactivite", None)
        context['box_titre'] = "Calendrier"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour définir les dates d'ouverture de l'activité. C'est également ici que vous pouvez définir la capacité d'accueil maximale par jour, par groupe et par unité de remplissage."
        context['onglet_actif'] = "calendrier"
        context['boutons_liste'] = [
            {"label": "Modifier", "classe": "btn btn-success", "href": reverse_lazy("activites_ouvertures", args=[idactivite]), "icone": "fa fa-pencil"},
        ]
        liste_colonnes, liste_lignes = self.Get_ouvertures(idactivite=idactivite)
        context['liste_colonnes'] = liste_colonnes
        context['liste_lignes'] = json.dumps(liste_lignes)
        context['idactivite'] = idactivite
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
        idannee = 10000
        for annee in liste_annees:
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
            idannee += 1
        return liste_colonnes, liste_lignes
