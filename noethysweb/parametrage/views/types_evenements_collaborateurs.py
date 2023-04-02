# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns
from core.views import crud
from core.models import TypeEvenementCollaborateur
from parametrage.forms.types_evenements_collaborateurs import Formulaire


class Page(crud.Page):
    model = TypeEvenementCollaborateur
    url_liste = "types_evenements_collaborateurs_liste"
    url_ajouter = "types_evenements_collaborateurs_ajouter"
    url_modifier = "types_evenements_collaborateurs_modifier"
    url_supprimer = "types_evenements_collaborateurs_supprimer"
    description_liste = "Voici ci-dessous la liste des catégories d'évènements pour les collaborateurs."
    description_saisie = "Saisissez toutes les informations concernant la catégorie à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une catégorie d'évènements"
    objet_pluriel = "des catégories d'évènements"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypeEvenementCollaborateur

    def get_queryset(self):
        return TypeEvenementCollaborateur.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idtype_evenement", "nom"]
        nom = columns.TextColumn("Nom", sources=["nom"], processor='Get_nom')
        type = columns.TextColumn("Type", sources=["type"], processor='Get_type')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idtype_evenement", "nom"]
            ordering = ["nom"]

        def Get_nom(self, instance, *args, **kwargs):
            return """<i class="fa fa-circle margin-r-5" style="color: %s"></i> %s""" % (instance.couleur, instance.nom)

        def Get_type(self, instance, *args, **kwargs):
            return instance.get_type_display()


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    pass
