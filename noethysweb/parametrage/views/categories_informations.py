# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import CategorieInformation
from parametrage.forms.categories_informations import Formulaire


class Page(crud.Page):
    model = CategorieInformation
    url_liste = "categories_informations_liste"
    url_ajouter = "categories_informations_ajouter"
    url_modifier = "categories_informations_modifier"
    url_supprimer = "categories_informations_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories d'informations personnelles."
    description_saisie = "Saisissez toutes les informations concernant la catégorie d'information personnelle à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie d'information personnelle"
    objet_pluriel = "des catégories d'informations personnelles"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = CategorieInformation

    def get_queryset(self):
        return CategorieInformation.objects.filter(self.Get_filtres("Q")).annotate(nbre_informations=Count("information"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_informations = columns.TextColumn("Informations associées", sources="nbre_informations")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "nom", "nbre_informations"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
