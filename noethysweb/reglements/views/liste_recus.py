# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Recu


class Page(crud.Page):
    model = Recu
    menu_code = "liste_recus"


class Liste(Page, crud.Liste):
    model = Recu

    def get_queryset(self):
        return Recu.objects.select_related('famille').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des reçus"
        context['box_titre'] = "Liste des reçus de règlements"
        context['box_introduction'] = "Voici ci-dessous la liste des reçus de règlements des familles."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idrecu", 'numero', 'date_edition']
        famille = columns.TextColumn("Famille", sources=['famille__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idrecu", 'numero', 'date_edition']
            processors = {
                'date_edition': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date_edition"]
