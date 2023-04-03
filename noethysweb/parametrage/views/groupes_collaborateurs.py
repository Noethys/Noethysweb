# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import GroupeCollaborateurs
from parametrage.forms.groupes_collaborateurs import Formulaire
from django.db.models import Count


class Page(crud.Page):
    model = GroupeCollaborateurs
    url_liste = "groupes_collaborateurs_liste"
    url_ajouter = "groupes_collaborateurs_ajouter"
    url_modifier = "groupes_collaborateurs_modifier"
    url_supprimer = "groupes_collaborateurs_supprimer"
    description_liste = "Voici ci-dessous la liste des groupes de collaborateurs."
    description_saisie = "Saisissez toutes les informations concernant le groupe à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un groupe de collaborateurs"
    objet_pluriel = "des groupes de collaborateurs"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = GroupeCollaborateurs

    def get_queryset(self):
        return GroupeCollaborateurs.objects.filter(self.Get_filtres("Q")).annotate(nbre_collaborateurs=Count("collaborateur_groupes"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idgroupe", "nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_collaborateurs = columns.TextColumn("Collaborateurs associés", sources="nbre_collaborateurs")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idgroupe", "nom", "nbre_collaborateurs"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
