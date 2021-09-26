# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import PortailDocument
from parametrage.forms.portail_documents import Formulaire


class Page(crud.Page):
    model = PortailDocument
    url_liste = "portail_documents_liste"
    url_ajouter = "portail_documents_ajouter"
    url_modifier = "portail_documents_modifier"
    url_supprimer = "portail_documents_supprimer"
    description_liste = "Voici ci-dessous la liste documents disponibles au téléchargement dans la page documents du portail."
    description_saisie = "Saisissez toutes les informations concernant le document et cliquez sur le bouton Enregistrer."
    objet_singulier = "un document"
    objet_pluriel = "des documents à télécharger"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = PortailDocument

    def get_queryset(self):
        return PortailDocument.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["iddocument", "titre", "texte"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["iddocument", "titre", "texte"]
            ordering = ["titre"]


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
