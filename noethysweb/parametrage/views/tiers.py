# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaTiers
from parametrage.forms.tiers import Formulaire


class Page(crud.Page):
    model = ComptaTiers
    url_liste = "tiers_liste"
    url_ajouter = "tiers_ajouter"
    url_modifier = "tiers_modifier"
    url_supprimer = "tiers_supprimer"
    description_liste = "Voici ci-dessous la liste des tiers."
    description_saisie = "Saisissez toutes les informations concernant le tiers à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un tiers"
    objet_pluriel = "des tiers"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ComptaTiers

    def get_queryset(self):
        return ComptaTiers.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtiers", "nom", "observations"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtiers", "nom", "observations"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
