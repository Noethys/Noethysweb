# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ComptaCompteComptable
from parametrage.forms.comptes_comptables import Formulaire


class Page(crud.Page):
    model = ComptaCompteComptable
    url_liste = "comptes_comptables_liste"
    url_ajouter = "comptes_comptables_ajouter"
    url_modifier = "comptes_comptables_modifier"
    url_supprimer = "comptes_comptables_supprimer"
    description_liste = "Voici ci-dessous la liste des comptes comptables."
    description_saisie = "Saisissez toutes les informations concernant le compte comptable à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un compte comptable"
    objet_pluriel = "des comptes comptables"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ComptaCompteComptable

    def get_queryset(self):
        return ComptaCompteComptable.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcompte", "nom", "numero"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcompte", "nom", "numero"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
