# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Individu
from fiche_individu.forms.individu_identite import Formulaire
from fiche_individu.views.individu import Onglet


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Identité"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        if not self.request.user.has_perm("core.individu_identite_modifier"):
            context['box_introduction'] = "Vous n'avez pas l'autorisation de modifier les informations de cette page."
        context['onglet_actif'] = "identite"
        return context

    def get_object(self):
        return Individu.objects.get(pk=self.kwargs['idindividu'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez les informations concernant l'identité de l'individu."
        return context

    def test_func_page(self):
        return self.request.user.has_perm("core.individu_identite_modifier")

    def get_success_url(self):
        # MAJ des infos des familles rattachées
        self.Maj_infos_famille()
        return reverse_lazy("individu_identite", kwargs={'idindividu': self.kwargs['idindividu'], 'idfamille': self.kwargs.get('idfamille', None)})
