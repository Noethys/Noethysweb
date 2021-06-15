# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import CategorieMedicale
from parametrage.forms.categories_medicales import Formulaire


class Page(crud.Page):
    model = CategorieMedicale
    url_liste = "categories_medicales_liste"
    url_ajouter = "categories_medicales_ajouter"
    url_modifier = "categories_medicales_modifier"
    url_supprimer = "categories_medicales_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories médicales."
    description_saisie = "Saisissez toutes les informations concernant la catégorie médicale à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie médicale"
    objet_pluriel = "des catégories médicales"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = CategorieMedicale

    def get_queryset(self):
        return CategorieMedicale.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "nom"]
            #hidden_columns = = ["idcategorie"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
