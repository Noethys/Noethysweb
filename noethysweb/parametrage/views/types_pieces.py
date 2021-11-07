# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.db.models import Count
from django.utils.dateparse import parse_date
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import TypePiece
from parametrage.forms.types_pieces import Formulaire


class Page(crud.Page):
    model = TypePiece
    url_liste = "types_pieces_liste"
    url_ajouter = "types_pieces_ajouter"
    url_modifier = "types_pieces_modifier"
    url_supprimer = "types_pieces_supprimer"
    description_liste = "Voici ci-dessous la liste des types de pièces."
    description_saisie = "Saisissez toutes les informations concernant le type de pièce à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un type de pièce"
    objet_pluriel = "des types de pièces"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = TypePiece

    def get_queryset(self):
        return TypePiece.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_pieces=Count("piece"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ['idtype_piece', 'nom', 'public']
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_standard')
        duree_validite = columns.DisplayColumn("Validité", sources="duree_validite", processor='Get_validite')
        nbre_pieces = columns.TextColumn("Pièces associées", sources="nbre_pieces")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idtype_piece', 'nom', 'public', 'duree_validite', "nbre_pieces"]
            ordering = ['nom']

        def Get_validite(self, instance, **kwargs):
            if instance.duree_validite == None:
                return "Illimitée"
            elif instance.duree_validite.startswith("j"):
                jours, mois, annees = instance.duree_validite.split("-")
                jours, mois, annees = int(jours[1:]), int(mois[1:]), int(annees[1:])
                liste_duree = []
                if annees > 0: liste_duree.append("%d années" % annees)
                if mois > 0: liste_duree.append("%d mois" % mois)
                if jours > 0: liste_duree.append("%d jours" % jours)
                return ", ".join(liste_duree)
            elif instance.duree_validite.startswith("d"):
                date = parse_date(instance.duree_validite[1:])
                return date.strftime('%d/%m/%Y')
            return ""

class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

class Modifier(Page, crud.Modifier):
    form_class = Formulaire

class Supprimer(Page, crud.Supprimer):
    manytomany_associes = [("activité(s)", "activite_types_pieces")]
