# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Activite
from parametrage.forms.activites_generalites import Formulaire
from parametrage.views.activites import Onglet



class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "parametrage/activite_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Généralités"
        context['box_introduction'] = "Voici les caractéristiques générales de l'activité : nom, période de validité, coordonnées, logo, structure... Cliquez sur le bouton Modifier pour les changer."
        context['onglet_actif'] = "generalites"
        return context

    def get_object(self):
        return Activite.objects.get(pk=self.kwargs['idactivite'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez les caractéristiques générales de l'activité. Le nom et le nom abrégé apparaissent dans toute l'application et sur le portail. Laissez les coordonnées et le logo identiques à ceux de l'organisateur, sauf si l'activité dispose des siens."
        return context

    def get_success_url(self):
        return reverse_lazy("activites_generalites", kwargs={'idactivite': self.kwargs['idactivite']})
