# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Restaurateur
from parametrage.forms.restaurateurs import Formulaire


class Page(crud.Page):
    model = Restaurateur
    url_liste = "restaurateurs_liste"
    url_ajouter = "restaurateurs_ajouter"
    url_modifier = "restaurateurs_modifier"
    url_supprimer = "restaurateurs_supprimer"
    description_liste = "Voici ci-dessous la liste des restaurateurs."
    description_saisie = "Saisissez toutes les informations concernant le restaurateur à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un restaurateur"
    objet_pluriel = "des restaurateurs"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Restaurateur

    def get_queryset(self):
        return Restaurateur.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idrestaurateur", "nom", "rue", "cp", "ville"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idrestaurateur", "nom", "rue", "cp", "ville"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
