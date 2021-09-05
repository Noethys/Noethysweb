# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from core.models import MenuCategorie
from parametrage.forms.menus_categories import Formulaire



class Page(crud.Page):
    model = MenuCategorie
    url_liste = "menus_categories_liste"
    url_ajouter = "menus_categories_ajouter"
    url_modifier = "menus_categories_modifier"
    url_supprimer = "menus_categories_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories de menus."
    description_saisie = "Saisissez toutes les informations concernant la catégorie de menu à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie de menu"
    objet_pluriel = "des catégories de menus"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Deplacer(Deplacer_lignes):
    model = MenuCategorie


class Liste(Page, crud.Liste):
    model = MenuCategorie

    def get_queryset(self):
        return MenuCategorie.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_deplacements'] = True
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcategorie", "ordre", "nom"]

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

    # def delete(self, request, *args, **kwargs):
    #     reponse = super(Supprimer, self).delete(request, *args, **kwargs)
    #     if reponse.status_code != 303:
    #         self.Reordonner()
    #     return reponse
