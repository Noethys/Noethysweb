# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypePosteCollaborateur
from parametrage.forms.types_postes_collaborateurs import Formulaire
from django.db.models import Count


class Page(crud.Page):
    model = TypePosteCollaborateur
    url_liste = "types_postes_collaborateurs_liste"
    url_ajouter = "types_postes_collaborateurs_ajouter"
    url_modifier = "types_postes_collaborateurs_modifier"
    url_supprimer = "types_postes_collaborateurs_supprimer"
    description_liste = "Voici ci-dessous la liste des types de postes pour les collaborateurs."
    description_saisie = "Saisissez toutes les informations concernant le type de poste à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de poste"
    objet_pluriel = "des types de postes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypePosteCollaborateur

    def get_queryset(self):
        return TypePosteCollaborateur.objects.filter(self.Get_filtres("Q")).annotate(nbre_contrats=Count("contratcollaborateur"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_poste", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_contrats = columns.TextColumn("Contrats associés", sources="nbre_contrats")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_poste", "nom", "nbre_contrats"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass