# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Activite
from parametrage.forms.activites_portail_parametres import Formulaire
from parametrage.views.activites import Onglet


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Paramètres du portail"
        context['box_introduction'] = "Voici les paramètres de l'activité sur le portail famille : inscriptions en ligne, réservations, délais de modification, validation et réattribution des places. Cliquez sur le bouton Modifier pour les changer."
        context['onglet_actif'] = "portail_parametres"
        return context

    def get_object(self):
        return Activite.objects.get(pk=self.kwargs['idactivite'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Indiquez si les familles peuvent s'inscrire et réserver depuis le portail, et jusqu'à quand elles peuvent ajouter ou supprimer une réservation. Pour proposer des réservations, vous devez également créer des périodes de réservation."
        return context

    def get_success_url(self):
        return reverse_lazy("activites_portail_parametres", kwargs={'idactivite': self.kwargs['idactivite']})
