# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from core.models import AchatCategorie
from parametrage.forms.achats_categories import Formulaire


class Page(crud.Page):
    model = AchatCategorie
    url_liste = "achats_categories_liste"
    url_ajouter = "achats_categories_ajouter"
    url_modifier = "achats_categories_modifier"
    url_supprimer = "achats_categories_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories d'articles pour les achats."
    description_saisie = "Saisissez toutes les informations concernant la catégorie à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie d'articles"
    objet_pluriel = "des catégories d'articles"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Deplacer(Deplacer_lignes):
    model = AchatCategorie


class Liste(Page, crud.Liste):
    model = AchatCategorie

    def get_queryset(self):
        return AchatCategorie.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_deplacements'] = True
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "ordre", "nom"]
            ordering = ["ordre"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
