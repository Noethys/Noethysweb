# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Aide
from fiche_famille.forms.famille_aides import Formulaire


class Page(crud.Page):
    model = Aide
    url_liste = "aides_liste"
    url_modifier = "famille_aides_modifier"
    url_supprimer = "famille_aides_supprimer"
    description_liste = "Voici ci-dessous la liste des aides des familles."
    description_saisie = "Saisissez toutes les informations concernant l'aide à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "une aide"
    objet_pluriel = "des aides"


class Liste(Page, crud.Liste):
    model = Aide

    def get_queryset(self):
        return Aide.objects.select_related("caisse", "activite", "activite__structure").prefetch_related("individus").filter(self.Get_filtres("Q"), famille__isnull=False)

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['page_titre'] = "Aides des familles"
        context['box_titre'] = "Liste des aides"
        return context

    class datatable_class(MyDatatable):
        filtres = ["fgenerique:famille", "idaide", "date_debut", "date_fin", "caisse__nom", "activite__nom"]
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        beneficiaires = columns.TextColumn("Bénéficiaires", sources=None, processor='Get_beneficiaires')
        caisse = columns.TextColumn("Caisse", sources=["caisse__nom"])
        activite = columns.TextColumn("Activité", sources=["activite__nom"])
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idaide", 'date_debut', 'date_fin', "famille", 'beneficiaires', 'caisse', 'activite']
            processors = {
                'date_debut': helpers.format_date('%d/%m/%Y'),
                'date_fin': helpers.format_date('%d/%m/%Y'),
            }
            ordering = ['date_debut']

        def Get_beneficiaires(self, instance, *args, **kwargs):
            return ", ".join([individu.Get_nom() for individu in instance.individus.all()])

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.famille_id, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.famille_id, instance.pk])),
                self.Create_bouton(url=reverse("famille_resume", args=[instance.famille_id]), title="Ouvrir la fiche famille", icone="fa-users"),
            ]
            return self.Create_boutons_actions(html)


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


class Supprimer(Page, crud.Supprimer):
    form_class = Formulaire
