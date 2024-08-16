# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views import crud
from core.models import Rattachement
from core.views.mydatatableview import MyDatatable, columns, helpers
from individus.views import certifications


class Liste(certifications.Page, crud.Liste):
    model = Rattachement

    def get_queryset(self):
        return Rattachement.objects.select_related("individu", "famille").filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "igenerique:individu", "certification_date"]
        check = columns.CheckBoxSelectColumn(label="")
        individu = columns.CompoundColumn("Individu", sources=["individu__nom", "individu__prenom"])
        famille = columns.TextColumn("Famille", sources=["famille__nom"])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idrattachement", "individu", "famille", "certification_date"]
            ordering = ["individu__nom", "individu__prenom"]
            processors = {
                "certification_date": helpers.format_date("%d/%m/%Y %H:%M"),
            }
            page_length = -1
