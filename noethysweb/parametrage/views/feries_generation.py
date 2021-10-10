# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from core.models import Ferie
from django.contrib import messages
from parametrage.forms.feries_generation import Formulaire
from dateutil.relativedelta import relativedelta
from dateutil.easter import easter
import datetime


class View(CustomView, TemplateView):
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Gestion des jours fériés variables"
        context['box_titre'] = "Génération automatique"
        context['box_introduction'] = "Sélectionnez un nombre d'années, l'année de début et les fériés souhaités avant de cliquer sur le bouton Générer."
        context['menu_actif'] = "feries_variables_liste"
        context['form'] = Formulaire
        return context

    def post(self, request):
        # Récupération des variables
        nbre_annees = int(request.POST.get("nombre"))
        annee_depart = int(request.POST.get("annee"))
        paques = request.POST.get("paques")
        ascension = request.POST.get("ascension")
        pentecote = request.POST.get("pentecote")

        # Vérifie qu'au moins un férié a été coché
        if not paques and not ascension and not pentecote:
            messages.add_message(self.request, messages.ERROR, "Génération impossible : Vous devez cocher au moins un férié !")
            return HttpResponseRedirect(reverse_lazy("feries_generation"))

        # Importation des fériés existants
        liste_feries_existants = []
        for ferie in Ferie.objects.filter(type='variable'):
            liste_feries_existants.append(datetime.date(year=ferie.annee, month=ferie.mois, day=ferie.jour))

        # Génération des fériés
        listeAnnees = range(annee_depart, annee_depart + nbre_annees)
        self.nbre_feries_crees = 0

        def Save_date(nom, date):
            if date not in liste_feries_existants:
                Ferie.objects.create(nom=nom, type="variable", jour=date.day, mois=date.month, annee=date.year)
                self.nbre_feries_crees += 1

        for annee in listeAnnees:

            # Dimanche de Paques
            dimanche_paques = easter(annee)

            # Lundi de Pâques
            lundi_paques = dimanche_paques + relativedelta(days=+1)
            if paques:
                Save_date(nom="Lundi de Pâques", date=lundi_paques)

            # Ascension
            ascension = dimanche_paques + relativedelta(days=+39)
            if ascension:
                Save_date(nom="Jeudi de l'Ascension", date=ascension)

            # Pentecote
            pentecote = dimanche_paques + relativedelta(days=+50)
            if pentecote:
                Save_date(nom="Lundi de Pentecôte", date=pentecote)

        messages.add_message(self.request, messages.SUCCESS, "%d jours fériés ont été générés automatiquement." % self.nbre_feries_crees)
        return HttpResponseRedirect(reverse_lazy("feries_variables_liste"))
