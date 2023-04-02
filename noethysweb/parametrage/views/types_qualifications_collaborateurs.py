# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypeQualificationCollaborateur
from parametrage.forms.types_qualifications_collaborateurs import Formulaire
from django.db.models import Count


class Page(crud.Page):
    model = TypeQualificationCollaborateur
    url_liste = "types_qualifications_collaborateurs_liste"
    url_ajouter = "types_qualifications_collaborateurs_ajouter"
    url_modifier = "types_qualifications_collaborateurs_modifier"
    url_supprimer = "types_qualifications_collaborateurs_supprimer"
    description_liste = "Voici ci-dessous la liste des types de qualifications pour les collaborateurs."
    description_saisie = "Saisissez toutes les informations concernant le type de qualification à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de qualification"
    objet_pluriel = "des types de qualifications"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeQualificationCollaborateur

    def get_queryset(self):
        return TypeQualificationCollaborateur.objects.filter(self.Get_filtres("Q")).annotate(nbre_collaborateurs=Count("collaborateur_qualifications"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_qualification", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_collaborateurs = columns.TextColumn("Collaborateurs associés", sources="nbre_collaborateurs")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_qualification", "nom", "nbre_collaborateurs"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("collaborateur(s)", "collaborateur_qualifications")]
