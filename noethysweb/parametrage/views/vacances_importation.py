# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from core.utils import utils_vacances
from core.models import Vacance
from django.contrib import messages


class View(CustomView, TemplateView):
    template_name = "parametrage/vacances_importation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des périodes de vacances"
        context['box_titre'] = "Importer depuis internet"
        context['box_introduction'] = "Sélectionnez une zone, cochez les périodes souhaitées puis cliquez sur le bouton Importer."
        context['menu_actif'] = "vacances_liste"

        # Récupération de la zone dans l'url
        zone = self.kwargs['zone']
        if zone in "abc":
            context['zone'] = zone.upper()
        else:
            context['zone'] = "A"

        # Importation des vacances existantes
        vacances_existantes = []
        for vacance in Vacance.objects.all():
            vacances_existantes.append((vacance.annee, vacance.nom))

        # Lecture du icalendar
        cal = utils_vacances.Calendrier(zone=context['zone'])
        self.listePeriodes = []

        # Vérifie que la période n'existe pas déjà
        for dict_vacance in cal.GetVacances():
            if ((dict_vacance["annee"], dict_vacance["nom"]) in vacances_existantes) == False :
                self.listePeriodes.append(dict_vacance)
        context['items'] = self.listePeriodes

        return context

    def post(self, request, zone="a"):
        # Récupération de la liste des périodes
        context = self.get_context_data()
        reponses = [int(id) for id in request.POST.getlist('items')]

        # Vérifie qu'au moins une réponse a été cochée
        if len(reponses) == 0:
            messages.add_message(self.request, messages.ERROR, "Importation impossible : Aucune période n'a été cochée !")
            return HttpResponseRedirect(reverse_lazy("vacances_importation", args=zone))

        # Sauvegarde des périodes cochées
        for index in reponses:
            dict_vacance = self.listePeriodes[index]
            Vacance.objects.create(nom=dict_vacance["nom"], annee=dict_vacance["annee"], date_debut=dict_vacance["date_debut"], date_fin=dict_vacance["date_fin"])
        return HttpResponseRedirect(reverse_lazy("vacances_liste"))
