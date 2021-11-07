# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Caisse
from parametrage.forms.caisses import Formulaire


class Page(crud.Page):
    model = Caisse
    url_liste = "caisses_liste"
    url_ajouter = "caisses_ajouter"
    url_modifier = "caisses_modifier"
    url_supprimer = "caisses_supprimer"
    description_liste = "Voici ci-dessous la liste des caisses."
    description_saisie = "Saisissez toutes les informations concernant la caisse à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une caisse"
    objet_pluriel = "des caisses"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Caisse

    def get_queryset(self):
        return Caisse.objects.filter(self.Get_filtres("Q")).annotate(nbre_familles=Count("famille"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcaisse", "nom", "regime__nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_familles = columns.TextColumn("Familles associées", sources="nbre_familles")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcaisse", "nom", "regime", "nbre_familles"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("tarif(s)", "tarif_caisses")]
