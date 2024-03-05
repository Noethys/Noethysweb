# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu


class Page(crud.Page):
    model = Individu
    url_liste = "liste_photos_manquantes"
    description_liste = "Voici ci-dessous la liste des photos manquantes. Utilisez la commande Filtrer pour cibler uniquement des inscrits ou présents à une ou plusieurs activités données."
    objet_singulier = "une photo manquante"
    objet_pluriel = "des photos manquantes"


class Liste(Page, crud.Liste):
    model = Individu

    def get_queryset(self):
        return Individu.objects.filter(self.Get_filtres("Q"), photo="")

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:pk", "idindividu"]

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idindividu", "nom", "prenom"]
            ordering = ["nom", "prenom"]
