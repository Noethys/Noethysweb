# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from core.views.base import CustomView
from core.utils import utils_vacances
from core.models import Vacance
from core.models import Organisateur


DICT_ZONES_SCOLAIRES = {
    "A": [25, 39, 70, 90, 24, 33, 40, 47, 64, 21, 58, 71, 89, 3, 15, 43, 63, 7, 26, 38, 73, 74, 19, 23, 87, 1, 42, 69, 16, 17, 79, 86],
    "B": [4, 5, 13, 84, 2, 60, 80, 14, 50, 61, 59, 62, 54, 55, 57, 88, 44, 49, 53, 72, 85, 6, 83, 18, 28, 36, 37, 41, 45, 8, 10, 51, 52, 22, 29, 35, 56, 27, 76, 67, 68],
    "C": [77, 93, 94, 75, 11, 30, 34, 48, 66, 9, 12, 31, 32, 46, 65, 81, 82, 78, 91, 92, 95],
}


def Rechercher_zone_scolaire(cp=""):
    for zone, liste_departements in DICT_ZONES_SCOLAIRES.items():
        if int((cp or None)[:2]) in liste_departements: return zone
    return None


class View(CustomView, TemplateView):
    template_name = "parametrage/vacances_importation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Gestion des périodes de vacances"
        context["box_titre"] = "Importer depuis internet"
        context["box_introduction"] = "Sélectionnez une zone, cochez les périodes souhaitées puis cliquez sur le bouton Importer."
        context["menu_actif"] = "vacances_liste"

        # Recherche de la zone de l'organisateur
        context["zone_organisateur"] = None
        organisateur = Organisateur.objects.filter(pk=1).first()
        if organisateur and organisateur.cp:
            context["zone_organisateur"] = Rechercher_zone_scolaire(organisateur.cp)

        # Récupération de la zone de l'URL
        context["zone"] = context["zone_organisateur"] or "A"
        if self.kwargs["zone"] in "abc":
            context["zone"] = self.kwargs["zone"].upper()

        # Récupération des périodes
        context["items"] = self.Get_liste_periodes(zone=context["zone"])

        return context

    def Get_liste_periodes(self, zone="a"):
        # Importation des vacances existantes
        vacances_existantes = [(vacance.annee, vacance.nom) for vacance in Vacance.objects.all()]

        # Lecture du icalendar
        cal = utils_vacances.Calendrier(zone=zone)

        # Récupération des périodes absentes
        liste_periodes = [dict_vacance for dict_vacance in cal.GetVacances() if not (dict_vacance["annee"], dict_vacance["nom"]) in vacances_existantes]
        return liste_periodes

    def post(self, request, zone="a"):
        # Récupération de la liste des périodes
        reponses = [int(id) for id in request.POST.getlist("items")]

        # Vérifie qu'au moins une réponse a été cochée
        if len(reponses) == 0:
            messages.add_message(self.request, messages.ERROR, "Importation impossible : Aucune période n'a été cochée !")
            return HttpResponseRedirect(reverse_lazy("vacances_importation", args=zone))

        # Sauvegarde des périodes cochées
        liste_periodes = self.Get_liste_periodes(zone=zone)
        for index in reponses:
            dict_vacance = liste_periodes[index]
            Vacance.objects.create(nom=dict_vacance["nom"], annee=dict_vacance["annee"], date_debut=dict_vacance["date_debut"], date_fin=dict_vacance["date_fin"])
        return HttpResponseRedirect(reverse_lazy("vacances_liste"))
