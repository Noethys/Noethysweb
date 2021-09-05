# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Classe
from parametrage.forms.classes import Formulaire


class Page(crud.Page):
    model = Classe
    url_liste = "classes_liste"
    url_ajouter = "classes_ajouter"
    url_modifier = "classes_modifier"
    url_supprimer = "classes_supprimer"
    description_liste = "Voici ci-dessous la liste des classes."
    description_saisie = "Saisissez toutes les informations concernant la classe à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une classe"
    objet_pluriel = "des classes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Classe

    def get_queryset(self):
        return Classe.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idclasse", "nom", "ecole__nom", "date_debut", "date_fin"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        ecole = columns.TextColumn("Ecole", sources=["ecole__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idclasse", "nom", "ecole", "date_debut", "date_fin"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_debut"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
