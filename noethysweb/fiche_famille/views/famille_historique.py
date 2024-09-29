# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.conf import settings
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Historique
from fiche_famille.views.famille import Onglet


class Page(Onglet):
    description_liste = "Vous pouvez consulter ici la liste des actions effectuées sur cette fiche famille."
    if settings.PURGE_HISTORIQUE_JOURS:
        description_liste += " Les actions sont mémorisées uniquement jusqu'à %d jours." % settings.PURGE_HISTORIQUE_JOURS

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Historique"
        context['onglet_actif'] = "outils"
        return context

class Liste(Page, crud.Liste):
    model = Historique
    template_name = "fiche_famille/famille_liste.html"

    def get_queryset(self):
        return Historique.objects.select_related("individu", "utilisateur").filter(Q(famille_id=self.Get_idfamille()) & self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        return context

    class datatable_class(MyDatatable):
        filtres = ['idaction', 'titre', 'detail', 'individu__nom']
        detail = columns.TextColumn("Détail", sources=[], processor='Formate_detail')
        utilisateur = columns.TextColumn("Utilisateur", sources=None, processor='Formate_utilisateur')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idaction', 'horodatage', 'utilisateur', 'titre', 'detail', 'individu']
            processors = {
                'horodatage': helpers.format_date('%d/%m/%Y %H:%M'),
            }
            ordering = ['horodatage']
            footer = False

        def Formate_detail(self, instance, **kwargs):
            return instance.detail

        def Formate_utilisateur(self, instance, **kwargs):
            if instance.utilisateur:
                return instance.utilisateur.get_full_name() or instance.utilisateur.get_short_name() or instance.utilisateur
            return ""
