# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views import crud
from core.models import Famille
from core.views.mydatatableview import MyDatatable, columns, helpers
from individus.views import certifications


class Liste(certifications.Page, crud.Liste):
    model = Famille

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "certification_date"]
        check = columns.CheckBoxSelectColumn(label="")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idfamille", "nom", "certification_date"]
            ordering = ["nom"]
            processors = {
                "certification_date": helpers.format_date("%d/%m/%Y %H:%M"),
            }
            page_length = -1
