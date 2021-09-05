# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ListeDiffusion
from parametrage.forms.listes_diffusion import Formulaire


class Page(crud.Page):
    model = ListeDiffusion
    url_liste = "listes_diffusion_liste"
    url_ajouter = "listes_diffusion_ajouter"
    url_modifier = "listes_diffusion_modifier"
    url_supprimer = "listes_diffusion_supprimer"
    description_liste = "Voici ci-dessous la liste des listes de diffusion."
    description_saisie = "Saisissez toutes les informations concernant la liste de diffusion à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une liste de diffusion"
    objet_pluriel = "des listes de diffusion"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = ListeDiffusion

    def get_queryset(self):
        return ListeDiffusion.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idliste", "nom"]

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idliste", "nom"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("individu(s)", "individu_listes_diffusion")]
