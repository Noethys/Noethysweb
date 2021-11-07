# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import CategorieTravail
from parametrage.forms.categories_travail import Formulaire


class Page(crud.Page):
    model = CategorieTravail
    url_liste = "categories_travail_liste"
    url_ajouter = "categories_travail_ajouter"
    url_modifier = "categories_travail_modifier"
    url_supprimer = "categories_travail_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories socio-professionnelles."
    description_saisie = "Saisissez toutes les informations concernant la catégorie socio-professionnelle à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie socio-professionnelle"
    objet_pluriel = "des catégories socio-professionnelles"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = CategorieTravail

    def get_queryset(self):
        return CategorieTravail.objects.filter(self.Get_filtres("Q")).annotate(nbre_individus=Count("individu"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_individus = columns.TextColumn("Individus associés", sources="nbre_individus")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcategorie", "nom", "nbre_individus"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
