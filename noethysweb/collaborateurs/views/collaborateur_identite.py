# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Collaborateur
from collaborateurs.forms.collaborateur_identite import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Identité"
        context['box_introduction'] = "Retrouvez ici l'état-civil du collaborateur, son mémo et sa photo. Cliquez sur le bouton Modifier pour mettre à jour ces informations."
        context['onglet_actif'] = "identite"
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez l'état-civil du collaborateur puis cliquez sur le bouton Enregistrer. Le nom de naissance n'est proposé que pour la civilité Madame."
        return context

    def get_success_url(self):
        return reverse_lazy("collaborateur_identite", kwargs={'idcollaborateur': self.kwargs['idcollaborateur']})
