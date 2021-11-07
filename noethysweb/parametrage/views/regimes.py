# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Regime
from parametrage.forms.regimes import Formulaire


class Page(crud.Page):
    model = Regime
    url_liste = "regimes_liste"
    url_ajouter = "regimes_ajouter"
    url_modifier = "regimes_modifier"
    url_supprimer = "regimes_supprimer"
    description_liste = "Voici ci-dessous la liste des régimes."
    description_saisie = "Saisissez toutes les informations concernant le régime à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un régime social"
    objet_pluriel = "des régimes sociaux"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Regime

    def get_queryset(self):
        return Regime.objects.filter(self.Get_filtres("Q")).annotate(nbre_familles=Count("caisse__famille"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idregime', 'nom']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_familles = columns.TextColumn("Familles associées", sources="nbre_familles")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idregime', 'nom', "nbre_familles"]
            ordering = ['nom']


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
