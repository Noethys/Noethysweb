# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Tache
from outils.forms.taches import Formulaire


class Page(crud.Page):
    model = Tache
    url_liste = "taches_liste"
    url_ajouter = "taches_ajouter"
    url_modifier = "taches_modifier"
    url_supprimer = "taches_supprimer"
    description_liste = "Voici ci-dessous la liste des tâches."
    description_saisie = "Saisissez toutes les informations concernant la tâche à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une tâche"
    objet_pluriel = "des tâches"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Tache

    def get_queryset(self):
        conditions = (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        return Tache.objects.filter(conditions, self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtache", "date", "titre"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtache", "date", "titre"]
            ordering = ["date"]
            processors = {
                "date": helpers.format_date("%d/%m/%Y"),
            }


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
