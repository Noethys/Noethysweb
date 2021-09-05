# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import FactureRegie
from parametrage.forms.regies import Formulaire



class Page(crud.Page):
    model = FactureRegie
    url_liste = "regies_liste"
    url_ajouter = "regies_ajouter"
    url_modifier = "regies_modifier"
    url_supprimer = "regies_supprimer"
    description_liste = "Voici ci-dessous la liste des régies."
    description_saisie = "Saisissez toutes les informations concernant la régie à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une régie"
    objet_pluriel = "des régies"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = FactureRegie

    def get_queryset(self):
        return FactureRegie.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idregie", "nom", "numclitipi", "compte_bancaire__nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        compte_bancaire = columns.TextColumn("Compte bancaire", sources=["compte_bancaire__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idregie", "nom", "numclitipi", "compte_bancaire"]
            ordering = ['nom']


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

