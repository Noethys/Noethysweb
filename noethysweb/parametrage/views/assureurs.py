# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Assureur
from parametrage.forms.assureurs import Formulaire
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Q, Count


class Page(crud.Page):
    model = Assureur
    url_liste = "assureurs_liste"
    url_ajouter = "assureurs_ajouter"
    url_modifier = "assureurs_modifier"
    url_supprimer = "assureurs_supprimer"
    description_liste = "Voici ci-dessous la liste des assureurs."
    description_saisie = "Saisissez toutes les informations concernant l'assureur à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un assureur"
    objet_pluriel = "des assureurs"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Assureur

    def get_queryset(self):
        from django.db.models import Q, Count
        return Assureur.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idassureur", "nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        # nbre_individus = columns.TextColumn("Nbre individus", sources="nbre_individus", processor='Formate_nbre_individus')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idassureur", "nom"]#, "nbre_individus"]
            ordering = ["nom"]

        # def Formate_nbre_individus(self, instance, **kwargs):
        #     return instance.nbre_individus


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
