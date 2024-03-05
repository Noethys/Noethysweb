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
    description_liste = "Voici ci-dessous la liste des régimes et des caisses des familles."
    menu_code = "liste_regimes_caisses"


class Liste(Page, crud.Liste):
    model = Famille

    def get_queryset(self):
        try:
            return Famille.objects.select_related("caisse", "allocataire", "caisse__regime").filter(self.Get_filtres("Q"))
        except:
            return Famille.objects.select_related("caisse", "allocataire", "caisse__regime")

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Régimes et caisses des familles"
        context['box_titre'] = "Liste des régimes et des caisses"
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:pk", "idfamille", "caisse__regime__nom", "caisse__nom", "num_allocataire", "allocataire__nom"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        caisse = columns.TextColumn("Caisse", sources=['caisse__nom'])
        regime = columns.TextColumn("Régime", sources=['caisse__regime__nom'])
        allocataire = columns.TextColumn("Allocataire titulaire", sources=['allocataire__nom', 'allocataire__prenom'])
        num_allocataire = columns.TextColumn("N° Allocataire", sources=None, processor='Get_num_allocataire')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfamille", "nom", "caisse", "regime", "num_allocataire", "allocataire"]
            ordering = ["nom"]

        def Get_num_allocataire(self, instance, *args, **kwargs):
            return instance.num_allocataire

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("famille_caisse", kwargs={"idfamille": instance.idfamille})),
            ]
            return self.Create_boutons_actions(html)
