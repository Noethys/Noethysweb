# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import JsonResponse
from core.views import crud
from core.models import Individu, RegimeAlimentaire
from fiche_individu.forms.individu_regimes_alimentaires import Formulaire
from fiche_individu.views.individu import Onglet


def Ajouter_regime_alimentaire(request):
    """ Ajouter un régime alimentaire """
    nom = request.POST.get("valeur")
    regime = RegimeAlimentaire.objects.create(nom=nom)
    return JsonResponse({"id": regime.pk, "valeur": regime.nom})


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Régimes alimentaires"
        context['box_introduction'] = "Cliquez sur le bouton Modifier pour modifier une des informations ci-dessous."
        if not self.request.user.has_perm("core.individu_regimes_alimentaires_modifier"):
            context['box_introduction'] = "Vous n'avez pas l'autorisation de modifier les informations de cette page."
        context['onglet_actif'] = "regimes_alimentaires"
        return context

    def get_object(self):
        return Individu.objects.get(pk=self.kwargs['idindividu'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Sélectionnez dans la liste déroulante les régimes alimentaires de l'individu."
        return context

    def test_func_page(self):
        return self.request.user.has_perm("core.individu_regimes_alimentaires_modifier")

    def get_success_url(self):
        # MAJ des infos des familles rattachées
        self.Maj_infos_famille()
        return reverse_lazy("individu_regimes_alimentaires", kwargs={'idindividu': self.kwargs['idindividu'], 'idfamille': self.kwargs.get('idfamille', None)})
