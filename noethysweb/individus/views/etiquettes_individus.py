# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Individu
from core.views.mydatatableview import MyDatatable, columns, helpers
from individus.views import etiquettes



class Liste(etiquettes.Page, crud.Liste):
    model = Individu

    def get_queryset(self):
        return Individu.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:pk", "iscolarise:pk", "idindividu", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid"]
        check = columns.CheckBoxSelectColumn(label="")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idindividu", "nom", "prenom", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

