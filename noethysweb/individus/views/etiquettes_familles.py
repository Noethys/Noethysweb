# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from core.models import Famille
from core.views.mydatatableview import MyDatatable, columns, helpers
from individus.views import etiquettes


class Liste(etiquettes.Page, crud.Liste):
    model = Famille

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['active_checkbox'] = True
        context['bouton_supprimer'] = False
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille"]
        check = columns.CheckBoxSelectColumn(label="")
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['check', "idfamille", "nom", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom"]

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid
