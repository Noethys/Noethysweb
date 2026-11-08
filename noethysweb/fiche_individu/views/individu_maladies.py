# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.http import JsonResponse
from core.views import crud
from core.models import Individu, TypeMaladie
from fiche_individu.forms.individu_maladies import Formulaire
from fiche_individu.views.individu import Onglet


def Ajouter_maladie(request):
    """ Ajouter un type de maladie """
    nom = request.POST.get("valeur")
    maladie = TypeMaladie.objects.create(nom=nom)
    return JsonResponse({"id": maladie.pk, "valeur": maladie.nom})


class Consulter(Onglet, crud.Modifier):
    form_class = Formulaire
    template_name = "fiche_individu/individu_edit.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Maladies"
        context['box_introduction'] = "Consultez ci-dessous les informations de cette rubrique. Cliquez sur le bouton Modifier pour les mettre à jour."
        if not self.request.user.has_perm("core.individu_maladies_modifier"):
            context['box_introduction'] = "Vous pouvez consulter ces informations mais vous n'avez pas l'autorisation de les modifier. Adressez-vous à un administrateur si besoin."
        context['onglet_actif'] = "maladies"
        return context

    def get_object(self):
        return Individu.objects.get(pk=self.kwargs['idindividu'])


class Modifier(Consulter):
    mode = "EDITION"

    def get_context_data(self, **kwargs):
        context = super(Modifier, self).get_context_data(**kwargs)
        context['box_introduction'] = "Sélectionnez les maladies déjà contractées par l'individu. Elles figurent notamment sur la fiche de renseignements."
        return context

    def test_func_page(self):
        return self.request.user.has_perm("core.individu_maladies_modifier")

    def get_success_url(self):
        # MAJ des infos des familles rattachées
        self.Maj_infos_famille()
        return reverse_lazy("individu_maladies", kwargs={'idindividu': self.kwargs['idindividu'], 'idfamille': self.kwargs.get('idfamille', None)})
