# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Vacance
from parametrage.forms.vacances import Formulaire



class Page(crud.Page):
    model = Vacance
    url_liste = "vacances_liste"
    url_ajouter = "vacances_ajouter"
    url_modifier = "vacances_modifier"
    url_supprimer = "vacances_supprimer"
    description_liste = "Voici ci-dessous la liste des périodes de vacances."
    description_saisie = "Saisissez toutes les informations concernant la période de vacances à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une période de vacances"
    objet_pluriel = "des périodes de vacances"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
        {"label": "Importer depuis internet", "classe": "btn btn-default", "href": reverse_lazy("vacances_importation", args="a"), "icone": "fa fa-download"}
    ]


class Liste(Page, crud.Liste):
    model = Vacance

    def get_queryset(self):
        return Vacance.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idvacance', 'nom', 'annee', 'date_debut', 'date_fin']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idvacance', 'nom', 'annee', 'date_debut', 'date_fin', 'actions']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass

