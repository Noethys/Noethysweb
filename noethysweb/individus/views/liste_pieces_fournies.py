# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Piece


class Page(crud.Page):
    model = Piece
    url_liste = "liste_pieces_fournies"
    description_liste = "Voici ci-dessous la liste des pièces fournies."
    objet_singulier = "une pièce fournie"
    objet_pluriel = "des pièces fournies"
    url_supprimer_plusieurs = "pieces_supprimer_plusieurs"


class Liste(Page, crud.Liste):
    # model = Piece

    def get_queryset(self):
        return Piece.objects.select_related("famille", "individu", "type_piece").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['active_checkbox'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "igenerique:individu", "idpiece", "date_debut", "date_fin", "type_piece__nom"]
        check = columns.CheckBoxSelectColumn(label="")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idpiece", "date_debut", "date_fin", "type_piece", "famille", "individu"]
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_debut"]


class Supprimer_plusieurs(Page, crud.Supprimer_plusieurs):
    pass
