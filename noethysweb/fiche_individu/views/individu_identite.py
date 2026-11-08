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
        context['box_introduction'] = "Consultez ci-dessous les informations de cette rubrique. Cliquez sur le bouton Modifier pour les mettre à jour."
        if not self.request.user.has_perm("core.individu_identite_modifier"):
            context['box_introduction'] = "Vous pouvez consulter ces informations mais vous n'avez pas l'autorisation de les modifier. Adressez-vous à un administrateur si besoin."
        context['onglet_actif'] = "identite"
        return context

    def get_object(self):
        return Individu.objects.get(pk=self.kwargs['idindividu'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Renseignez l'état civil de l'individu : civilité, nom, prénom, date et lieu de naissance."
        return context

    def test_func_page(self):
        return self.request.user.has_perm("core.individu_identite_modifier")

    def get_success_url(self):
        # MAJ des infos des familles rattachées
        self.Maj_infos_famille()
        return reverse_lazy("individu_identite", kwargs={'idindividu': self.kwargs['idindividu'], 'idfamille': self.kwargs.get('idfamille', None)})
