# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from django.db.models import Count
from core.views import crud
from core.models import LotFactures
from parametrage.forms.lots_factures import Formulaire


class Page(crud.Page):
    model = LotFactures
    url_liste = "lots_factures_liste"
    url_ajouter = "lots_factures_ajouter"
    url_modifier = "lots_factures_modifier"
    url_supprimer = "lots_factures_supprimer"
    description_liste = "Voici ci-dessous la liste des lots de factures."
    description_saisie = "Saisissez toutes les informations concernant le lot à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un lot de factures"
    objet_pluriel = "des lots de factures"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = LotFactures

    def get_queryset(self):
        return LotFactures.objects.filter(self.Get_filtres("Q")).annotate(nbre_factures=Count("facture"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idlot", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_factures = columns.TextColumn("Factures associées", sources="nbre_factures")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idlot", "nom", "nbre_factures", "actions"]
            ordering = ['nom']


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

