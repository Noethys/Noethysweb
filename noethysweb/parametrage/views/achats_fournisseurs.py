# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import AchatFournisseur
from parametrage.forms.achats_fournisseurs import Formulaire


class Page(crud.Page):
    model = AchatFournisseur
    url_liste = "achats_fournisseurs_liste"
    url_ajouter = "achats_fournisseurs_ajouter"
    url_modifier = "achats_fournisseurs_modifier"
    url_supprimer = "achats_fournisseurs_supprimer"
    description_liste = "Voici ci-dessous la liste des fournisseurs."
    description_saisie = "Saisissez toutes les informations concernant le fournisseur à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un fournisseur"
    objet_pluriel = "des fournisseurs"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = AchatFournisseur

    def get_queryset(self):
        return AchatFournisseur.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idfournisseur", "nom", "observations"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfournisseur", "nom", "observations"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
