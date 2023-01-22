# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Count
from django.utils.dateparse import parse_date
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ModelePrestation
from parametrage.forms.modeles_prestations import Formulaire


class Page(crud.Page):
    model = ModelePrestation
    url_liste = "modeles_prestations_liste"
    url_ajouter = "modeles_prestations_ajouter"
    url_modifier = "modeles_prestations_modifier"
    url_supprimer = "modeles_prestations_supprimer"
    description_liste = "Voici ci-dessous la liste des modèles de prestations."
    description_saisie = "Saisissez toutes les informations concernant le modèle de prestation à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle de prestation"
    objet_pluriel = "des modèles de prestations"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ModelePrestation

    def get_queryset(self):
        return ModelePrestation.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmodele", "label", "public"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        public = columns.TextColumn("Public", sources=["public"], processor="Formate_public")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmodele", "label", "public"]
            ordering = ["label"]

        def Formate_public(self, instance, **kwargs):
            return instance.get_public_display()


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
