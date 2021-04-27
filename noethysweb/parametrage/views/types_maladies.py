# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypeMaladie
from parametrage.forms.types_maladies import Formulaire


class Page(crud.Page):
    model = TypeMaladie
    url_liste = "types_maladies_liste"
    url_ajouter = "types_maladies_ajouter"
    url_modifier = "types_maladies_modifier"
    url_supprimer = "types_maladies_supprimer"
    description_liste = "Voici ci-dessous la liste des types de maladies."
    description_saisie = "Saisissez toutes les informations concernant la maladie à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de maladie"
    objet_pluriel = "des types de maladie"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeMaladie

    def get_queryset(self):
        return TypeMaladie.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_maladie", "nom", "vaccin_obligatoire"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_maladie", "nom", "vaccin_obligatoire"]
            #hidden_columns = = ["idtype_maladie"]
            ordering = ["nom"]

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
