# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import RegimeAlimentaire, Individu
from parametrage.forms.types_regimes_alimentaires import Formulaire
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Q, Count


class Page(crud.Page):
    model = RegimeAlimentaire
    url_liste = "types_regimes_alimentaires_liste"
    url_ajouter = "types_regimes_alimentaires_ajouter"
    url_modifier = "types_regimes_alimentaires_modifier"
    url_supprimer = "types_regimes_alimentaires_supprimer"
    description_liste = "Voici ci-dessous la liste des types de régimes alimentaires."
    description_saisie = "Saisissez toutes les informations concernant le type de régime alimentaire à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de régime alimentaire"
    objet_pluriel = "des types de régimes alimentaires"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = RegimeAlimentaire

    def get_queryset(self):
        from django.db.models import Q, Count
        return RegimeAlimentaire.objects.filter(self.Get_filtres("Q")).annotate(nbre_individus=Count('individu_regimes_alimentaires'))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_regime", "nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_individus = columns.TextColumn("Individus associés", sources="nbre_individus")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_regime", "nom", "nbre_individus"]
            ordering = ["nom"]
            labels = {
                "nom": "Nom du régime",
            }


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    def delete(self, request, *args, **kwargs):
        """ Empêche la suppression du type de régime s'il est déjà associé à au moins un individu """
        resultat = RegimeAlimentaire.objects.filter(pk=self.get_object().pk).aggregate(nbre_individus=Count('individu_regimes_alimentaires'))
        if resultat["nbre_individus"] > 0:
            messages.add_message(request, messages.ERROR, "Il est impossible de supprimer ce régime car il est déjà associé à %d individu(s) !" % resultat["nbre_individus"])
            return HttpResponseRedirect(self.get_success_url(), status=303)
        return super(Supprimer, self).delete(request, *args, **kwargs)
