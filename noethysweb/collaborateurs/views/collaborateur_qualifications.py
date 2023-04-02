# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Collaborateur
from collaborateurs.forms.collaborateur_qualifications import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Qualifications"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        context['onglet_actif'] = "qualifications"
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Sélectionnez dans la liste déroulante les qualifications du collaborateur."
        return context

    def get_success_url(self):
        return reverse_lazy("collaborateur_qualifications", kwargs={'idcollaborateur': self.kwargs['idcollaborateur']})
