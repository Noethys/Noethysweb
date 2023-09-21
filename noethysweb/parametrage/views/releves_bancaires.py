# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaReleve
from parametrage.forms.releves_bancaires import Formulaire


class Page(crud.Page):
    model = ComptaReleve
    url_liste = "releves_bancaires_liste"
    url_ajouter = "releves_bancaires_ajouter"
    url_modifier = "releves_bancaires_modifier"
    url_supprimer = "releves_bancaires_supprimer"
    description_liste = "Voici ci-dessous la liste des relevés bancaires."
    description_saisie = "Saisissez toutes les informations concernant le relevé à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un relevé bancaire"
    objet_pluriel = "des relevés bancaires"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ComptaReleve

    def get_queryset(self):
        return ComptaReleve.objects.filter(self.Get_filtres("Q")).annotate(nbre_operations=Count("comptaoperation"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idreleve", "nom", "date_debut", "date_fin", "compte__nom"]
        nbre_operations = columns.TextColumn("Nbre", sources="nbre_operations")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idreleve", "nom", "date_debut", "date_fin", "compte", "nbre_operations", "actions"]
            ordering = ["date_debut"]
            processors = {
                "date_debut": helpers.format_date("%d/%m/%Y"),
                "date_fin": helpers.format_date("%d/%m/%Y"),
            }


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
