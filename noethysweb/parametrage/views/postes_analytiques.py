# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaAnalytique
from parametrage.forms.postes_analytiques import Formulaire


class Page(crud.Page):
    model = ComptaAnalytique
    url_liste = "postes_analytiques_liste"
    url_ajouter = "postes_analytiques_ajouter"
    url_modifier = "postes_analytiques_modifier"
    url_supprimer = "postes_analytiques_supprimer"
    description_liste = "Voici ci-dessous la liste des postes analytiques."
    description_saisie = "Saisissez toutes les informations concernant le poste analytique à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un poste analytique"
    objet_pluriel = "des postes analytiques"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ComptaAnalytique

    def get_queryset(self):
        return ComptaAnalytique.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idanalytique", "nom", "abrege"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idanalytique", "nom", "abrege"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
