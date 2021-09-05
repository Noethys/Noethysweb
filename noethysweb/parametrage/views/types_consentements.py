# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypeConsentement
from parametrage.forms.types_consentements import Formulaire


class Page(crud.Page):
    model = TypeConsentement
    url_liste = "types_consentements_liste"
    url_ajouter = "types_consentements_ajouter"
    url_modifier = "types_consentements_modifier"
    url_supprimer = "types_consentements_supprimer"
    description_liste = "Voici ci-dessous la liste des types de consentements. Ils sont généralement utilisés sur le portail pour faire valider aux usagers les conditions d'utilisation de la structure."
    description_saisie = "Saisissez toutes les informations concernant le type de consentement à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de consentement"
    objet_pluriel = "des types de consentements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeConsentement

    def get_queryset(self):
        return TypeConsentement.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idtype_consentement', 'nom']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idtype_consentement', 'nom']
            ordering = ['nom']


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("activité(s)", "activite_types_consentements")]
