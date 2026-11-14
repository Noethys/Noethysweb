# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from parametrage.views.valeurs_defaut_collaborateurs import Bouton as Bouton_valeurs_defaut
from core.models import TypeContratCollaborateur
from parametrage.forms.types_contrats_collaborateurs import Formulaire
from django.db.models import Count


class Page(crud.Page):
    model = TypeContratCollaborateur
    url_liste = "types_contrats_collaborateurs_liste"
    url_ajouter = "types_contrats_collaborateurs_ajouter"
    url_modifier = "types_contrats_collaborateurs_modifier"
    url_supprimer = "types_contrats_collaborateurs_supprimer"
    description_liste = "Les types de contrats décrivent la nature des contrats des collaborateurs (CDI, CDD, contrat d'engagement éducatif...)."
    description_saisie = "Saisissez le nom du type de contrat puis cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de contrat"
    objet_pluriel = "des types de contrats"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
        Bouton_valeurs_defaut("types_contrats"),
    ]


class Liste(Page, crud.Liste):
    model = TypeContratCollaborateur

    def get_queryset(self):
        return TypeContratCollaborateur.objects.filter(self.Get_filtres("Q")).annotate(nbre_contrats=Count("contratcollaborateur"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_contrat", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_contrats = columns.TextColumn("Contrats associés", sources="nbre_contrats")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_contrat", "nom", "nbre_contrats"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass