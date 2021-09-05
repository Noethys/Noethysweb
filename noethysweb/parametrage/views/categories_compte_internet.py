# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import CategorieCompteInternet
from parametrage.forms.categories_compte_internet import Formulaire
from django.db.models import Q, Count


class Page(crud.Page):
    model = CategorieCompteInternet
    url_liste = "categories_compte_internet_liste"
    url_ajouter = "categories_compte_internet_ajouter"
    url_modifier = "categories_compte_internet_modifier"
    url_supprimer = "categories_compte_internet_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories de compte internet."
    description_saisie = "Saisissez toutes les informations concernant la catégorie à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie de compte internet"
    objet_pluriel = "des catégories de compte internet"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = CategorieCompteInternet

    def get_queryset(self):
        return CategorieCompteInternet.objects.annotate(nbre_familles=Count('internet_categorie'))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_familles = columns.TextColumn("Familles associées", sources="nbre_familles")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "nom", "nbre_familles"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("période(s)", "periode_categories")]
