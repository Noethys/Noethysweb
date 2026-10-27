# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import TypeGroupeActivite
from parametrage.forms.types_groupes_activites import Formulaire


class Page(crud.Page):
    model = TypeGroupeActivite
    url_liste = "types_groupes_activites_liste"
    url_ajouter = "types_groupes_activites_ajouter"
    url_modifier = "types_groupes_activites_modifier"
    url_supprimer = "types_groupes_activites_supprimer"
    description_liste = "Les groupes d'activités permettent de sélectionner rapidement un ensemble d'activités (exemples : Périscolaire, Vacances, Sport et culture) dans les états, listes, statistiques et générations de factures. Une activité peut appartenir à plusieurs groupes."
    description_saisie = "Saisissez le nom du groupe d'activités et sélectionnez les activités qui en font partie, puis cliquez sur le bouton Enregistrer."
    objet_singulier = "un groupe d'activités"
    objet_pluriel = "des groupes d'activités"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeGroupeActivite

    def get_queryset(self):
        return TypeGroupeActivite.objects.select_related("structure").filter(self.Get_filtres("Q"), structure__in=self.request.user.structures.all()) \
                .annotate(nbre_activites=Count("activite_groupes_activites", distinct=True))


    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_groupe_activite", "nom", "nbre_activites"]
        nbre_activites = columns.TextColumn("Activités associées", sources="nbre_activites")
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_groupe_activite", "nom"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("activité(s)", "activite_groupes_activites")]
