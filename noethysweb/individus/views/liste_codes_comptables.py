# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille


class Page(crud.Page):
    model = Famille
    description_liste = "Voici ci-dessous la liste des codes comptables des familles."


class Liste(Page, crud.Liste):
    model = Famille

    def get_queryset(self):
        return Famille.objects.filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Codes comptables des familles"
        context['box_titre'] = "Liste des codes comptables"
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idfamille", "code_compta"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfamille", "nom", "code_compta"]
            ordering = ["nom"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_divers", kwargs={"idfamille": instance.idfamille})),
            ]
            return self.Create_boutons_actions(html)
