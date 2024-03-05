# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q, Count
from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille


class Page(crud.Page):
    model = Famille
    description_liste = "Voici ci-dessous la liste des familles dont aucun des membres n'est inscrit à une activité."


class Liste(Page, crud.Liste):
    model = Famille

    def get_queryset(self):
        liste_familles = Famille.objects.values("nom", "pk").annotate(nbre=Count("rattachement__individu__inscription", distinct=True)).filter(nbre=0).order_by("nbre")
        return Famille.objects.filter(pk__in=[dict_famille["pk"] for dict_famille in liste_familles]).filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Liste des familles sans inscriptions"
        context['box_titre'] = "Liste des familles"
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idfamille"]
        rue_resid = columns.TextColumn("Rue", processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idfamille", "nom", "rue_resid", "cp_resid", "ville_resid", "actions"]
            ordering = ["nom"]

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton(url=reverse("famille_resume", args=[instance.pk]), title="Ouvrir la fiche famille", icone="fa-users"),
            ]
            return self.Create_boutons_actions(html)
