# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Note
from outils.forms.notes import Formulaire


class Page(crud.Page):
    model = Note
    url_liste = "notes_liste"
    url_ajouter = "notes_ajouter"
    url_modifier = "notes_modifier"
    url_supprimer = "notes_supprimer"
    description_liste = "Voici ci-dessous la liste des notes."
    description_saisie = "Saisissez toutes les informations concernant la note à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une note"
    objet_pluriel = "des notes"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Note

    def get_queryset(self):
        conditions = (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        return Note.objects.select_related("famille", "individu", "collaborateur").filter(conditions, self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idnote", "date_parution", "texte", "famille__nom", "individu__nom", "date_saisie", "afficher_accueil", "afficher_liste", "rappel", "afficher_facture", "rappel_famille", "afficher_commande"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        famille = columns.TextColumn("Famille", sources=['famille__nom'])
        individu = columns.TextColumn("Individu", sources=['individu__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idnote", "date_parution", "texte", "famille", "individu"]
            ordering = ["date_parution"]
            processors = {
                'date_parution': helpers.format_date('%d/%m/%Y'),
            }


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    pass
