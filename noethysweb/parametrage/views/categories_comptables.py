# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaCategorie
from parametrage.forms.categories_comptables import Formulaire


class Page(crud.Page):
    model = ComptaCategorie
    url_liste = "categories_comptables_liste"
    url_ajouter = "categories_comptables_ajouter"
    url_modifier = "categories_comptables_modifier"
    url_supprimer = "categories_comptables_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories comptables."
    description_saisie = "Saisissez toutes les informations concernant la catégorie comptable à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un catégorie comptable"
    objet_pluriel = "des catégories comptables"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ComptaCategorie

    def get_queryset(self):
        return ComptaCategorie.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "type", "nom", "abrege"]
        type = columns.TextColumn("Type", sources=["type"], processor='Get_type')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "type", "nom", "abrege", "compte_comptable"]
            ordering = ["nom"]

        def Get_type(self, instance, *args, **kwargs):
            return instance.get_type_display()


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
