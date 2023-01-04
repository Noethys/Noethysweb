# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Tache_recurrente
from parametrage.forms.taches_recurrentes import Formulaire


class Page(crud.Page):
    model = Tache_recurrente
    url_liste = "taches_recurrentes_liste"
    url_ajouter = "taches_recurrentes_ajouter"
    url_modifier = "taches_recurrentes_modifier"
    url_supprimer = "taches_recurrentes_supprimer"
    description_liste = "Voici ci-dessous la liste des tâches récurrentes."
    description_saisie = "Saisissez toutes les informations concernant la tâche récurrente à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une tâche récurrente"
    objet_pluriel = "des tâches récurrentes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Tache_recurrente

    def get_queryset(self):
        return Tache_recurrente.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtache_recurrente", "titre", "date_debut", "date_fin"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtache_recurrente", "titre", "date_debut", "date_fin"]
            processors = {
                'date_debut': helpers.format_date("%d/%m/%Y"),
                'date_fin': helpers.format_date("%d/%m/%Y"),
            }
            ordering = ["date_debut"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
