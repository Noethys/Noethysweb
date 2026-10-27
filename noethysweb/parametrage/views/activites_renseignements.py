# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Activite
from parametrage.forms.activites_renseignements import Formulaire
from parametrage.views.activites import Onglet


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Renseignements"
        context['box_introduction'] = "Voici les renseignements et les pièces exigés des individus inscrits à cette activité. Les éléments manquants sont signalés dans les fiches et dans les alertes. Cliquez sur le bouton Modifier pour les changer."
        context['onglet_actif'] = "renseignements"
        return context

    def get_object(self):
        return Activite.objects.get(pk=self.kwargs['idactivite'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Sélectionnez les pièces, adhésions, vaccinations, assurances et consentements qu'un individu inscrit à cette activité doit fournir. Les éléments manquants seront signalés dans les fiches et dans les alertes."
        return context

    def get_success_url(self):
        return reverse_lazy("activites_renseignements", kwargs={'idactivite': self.kwargs['idactivite']})
