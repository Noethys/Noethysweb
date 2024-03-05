# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Individu
from core.utils import utils_dates


class Page(crud.Page):
    model = Individu
    url_liste = "individus_detaches_liste"
    url_supprimer = "individus_detaches_supprimer"
    description_liste = "Voici ci-dessous la liste des individus détachés."
    objet_singulier = "un individu détaché"
    objet_pluriel = "des individus détachés"


class Liste(Page, crud.Liste):
    model = Individu

    def get_queryset(self):
        return Individu.objects.filter(rattachement__isnull=True).filter(self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ["igenerique:pk",]
        idindividu = columns.IntegerColumn("ID", sources=['pk'])
        # nom = columns.TextColumn("Nom", sources=['nom'])
        # prenom = columns.TextColumn("Prénom", sources=['prenom'])
        date_naiss = columns.TextColumn("Date naiss.", sources=None, processor='Get_date_naiss')
        rue_resid = columns.TextColumn("Rue", sources=None, processor='Get_rue_resid')
        cp_resid = columns.TextColumn("CP", sources=None, processor='Get_cp_resid')
        ville_resid = columns.TextColumn("Ville", sources=None, processor='Get_ville_resid')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idindividu', "nom", "prenom", "date_naiss", "rue_resid", "cp_resid", "ville_resid"]
            ordering = ["nom", "prenom"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                # self.Create_bouton(url=reverse("individu_resume", args=[0, instance.pk]), title="Ouvrir la fiche individuelle", icone="fa-user"),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)

        def Get_date_naiss(self, instance, *args, **kwargs):
            return utils_dates.ConvertDateToFR(instance.date_naiss)

        def Get_rue_resid(self, instance, *args, **kwargs):
            return instance.rue_resid

        def Get_cp_resid(self, instance, *args, **kwargs):
            return instance.cp_resid

        def Get_ville_resid(self, instance, *args, **kwargs):
            return instance.ville_resid


class Supprimer(Page, crud.Supprimer):
    pass
