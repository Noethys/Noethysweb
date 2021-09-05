# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Ecole
from parametrage.forms.ecoles import Formulaire


class Page(crud.Page):
    model = Ecole
    url_liste = "ecoles_liste"
    url_ajouter = "ecoles_ajouter"
    url_modifier = "ecoles_modifier"
    url_supprimer = "ecoles_supprimer"
    description_liste = "Voici ci-dessous la liste des écoles."
    description_saisie = "Saisissez toutes les informations concernant l'école à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une école"
    objet_pluriel = "des écoles"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Ecole

    def get_queryset(self):
        return Ecole.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idecole", "nom", "rue", "cp", "ville"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idecole", "nom", "rue", "cp", "ville"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
