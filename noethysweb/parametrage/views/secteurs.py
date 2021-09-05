# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Secteur
from parametrage.forms.secteurs import Formulaire


class Page(crud.Page):
    model = Secteur
    url_liste = "secteurs_liste"
    url_ajouter = "secteurs_ajouter"
    url_modifier = "secteurs_modifier"
    url_supprimer = "secteurs_supprimer"
    description_liste = "Voici ci-dessous la liste des secteurs géographiques."
    description_saisie = "Saisissez toutes les informations concernant le secteur géographique à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un secteur géographique"
    objet_pluriel = "des secteurs géographiques"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Secteur

    def get_queryset(self):
        return Secteur.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idsecteur", "nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idsecteur", "nom"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("école(s)", "ecole_secteurs")]
