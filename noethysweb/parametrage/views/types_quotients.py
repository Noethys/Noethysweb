# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypeQuotient
from parametrage.forms.types_quotients import Formulaire


class Page(crud.Page):
    model = TypeQuotient
    url_liste = "types_quotients_liste"
    url_ajouter = "types_quotients_ajouter"
    url_modifier = "types_quotients_modifier"
    url_supprimer = "types_quotients_supprimer"
    description_liste = "Voici ci-dessous la liste des types de quotients."
    description_saisie = "Saisissez toutes les informations concernant le type de quotient à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de quotient"
    objet_pluriel = "des types de quotients"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeQuotient

    def get_queryset(self):
        return TypeQuotient.objects.filter(self.Get_filtres("Q")).annotate(nbre_quotients=Count("quotient"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_quotient", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_quotients = columns.TextColumn("Quotients associés", sources="nbre_quotients")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_quotient", "nom", "nbre_quotients"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
