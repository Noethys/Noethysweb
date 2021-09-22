# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Medecin
from parametrage.forms.medecins import Formulaire


class Page(crud.Page):
    model = Medecin
    url_liste = "medecins_liste"
    url_ajouter = "medecins_ajouter"
    url_modifier = "medecins_modifier"
    url_supprimer = "medecins_supprimer"
    description_liste = "Voici ci-dessous la liste des médecins."
    description_saisie = "Saisissez toutes les informations concernant le médecin à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un médecin"
    objet_pluriel = "des médecins"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Medecin

    def get_queryset(self):
        return Medecin.objects.filter(self.Get_filtres("Q")).annotate(nbre_individus=Count("individu"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmedecin", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid", "tel_cabinet"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nbre_individus = columns.TextColumn("Individus associés", sources="nbre_individus")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmedecin", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid", "tel_cabinet", "nbre_individus"]
            ordering = ["nom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
