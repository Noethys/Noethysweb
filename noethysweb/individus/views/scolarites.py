# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Scolarite
from fiche_individu.forms.individu_scolarite import Formulaire


class Page(crud.Page):
    model = Scolarite
    url_liste = "scolarites_liste"
    url_ajouter = "scolarites_ajouter"
    url_modifier = "scolarites_modifier"
    url_supprimer = "scolarites_supprimer"
    description_liste = "Voici ci-dessous la liste des étapes de scolarité."
    description_saisie = "Saisissez toutes les informations concernant l'étape de scolarité à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une étape de scolarité"
    objet_pluriel = "des étapes de scolarité"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Scolarite

    def get_queryset(self):
        return Scolarite.objects.select_related("individu", "ecole", "classe").prefetch_related("niveau").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:individu", 'idscolarite', 'date_debut', 'date_fin', 'ecole__nom', 'classe__nom', 'niveau__abrege']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        nom = columns.TextColumn("Nom", sources=["individu__nom"])
        prenom = columns.TextColumn("Prénom", sources=["individu__prenom"])
        date_naiss = columns.TextColumn("Date naiss.", sources=None, processor=helpers.format_date('%d/%m/%Y'))
        ecole = columns.TextColumn("Ecole", sources=["ecole__nom"])
        classe = columns.TextColumn("Classe", sources=["classe__nom"])
        niveau = columns.TextColumn("Niveau", sources=["niveau__abrege"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idscolarite", "nom", "prenom", "date_naiss", "date_debut", "date_fin", "ecole", "classe", "niveau"]
            hidden_columns = ["date_naiss"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["nom", "prenom"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
