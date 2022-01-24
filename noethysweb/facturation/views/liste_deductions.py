# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Deduction


class Page(crud.Page):
    model = Deduction
    url_liste = "prestations_liste"
    description_liste = "Voici ci-dessous la liste des déductions."
    objet_singulier = "une déduction"
    objet_pluriel = "des déductions"


class Liste(Page, crud.Liste):
    model = Deduction

    def get_queryset(self):
        return Deduction.objects.select_related('prestation', 'prestation__activite').filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["ipresent:prestation__individu", "fpresent:famille", "iscolarise:prestation__individu", "fscolarise:famille", "iddeduction", "date", "label", "famille__nom", "individu__nom", "montant"]

        activite = columns.TextColumn("Activité", sources=['prestation__activite__nom'])
        individu = columns.CompoundColumn("Individu", sources=['prestation__individu__nom', 'prestation__individu__prenom'])
        famille = columns.TextColumn("Famille", sources=['famille__nom'])

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["iddeduction", "date", "label", "famille", "individu", "montant", "activite"]
            processors = {
                'date': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ["date"]


