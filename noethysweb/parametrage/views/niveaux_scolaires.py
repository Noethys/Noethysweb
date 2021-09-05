# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns, helpers, Deplacer_lignes
from core.views import crud
from core.models import NiveauScolaire
from parametrage.forms.niveaux_scolaires import Formulaire


class Page(crud.Page):
    model = NiveauScolaire
    url_liste = "niveaux_scolaires_liste"
    url_ajouter = "niveaux_scolaires_ajouter"
    url_modifier = "niveaux_scolaires_modifier"
    url_supprimer = "niveaux_scolaires_supprimer"
    description_liste = "Voici ci-dessous la liste des niveaux scolaires."
    description_saisie = "Saisissez toutes les informations concernant le niveau scolaire à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un niveau scolaire"
    objet_pluriel = "des niveaux scolaires"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Deplacer(Deplacer_lignes):
    model = NiveauScolaire


class Liste(Page, crud.Liste):
    model = NiveauScolaire

    def get_queryset(self):
        return NiveauScolaire.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_deplacements'] = True
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idniveau", "nom", "abrege"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idniveau", "ordre", "nom", "abrege"]
            ordering = ["ordre"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("classe(s)", "classe_niveaux")]
