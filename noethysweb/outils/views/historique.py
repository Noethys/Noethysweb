# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Famille, Historique
from core.utils import utils_parametres


class Page(crud.Page):
    description_liste = "Vous pouvez consulter ici la liste des actions effectuées dans le logiciel."
    menu_code = "historique"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Historique"
        context['box_titre'] = "Historique général"
        context['onglet_actif'] = "outils"
        return context


class Liste(Page, crud.Liste):
    model = Historique
    template_name = "outils/historique.html"

    def get_queryset(self):
        conditions = (Q(utilisateur__structures__in=self.request.user.structures.all()) | Q(utilisateur__categorie="famille"))
        self.afficher_dernier_mois = utils_parametres.Get(nom="afficher_dernier_mois", categorie="historique", utilisateur=self.request.user, valeur=True)
        if self.afficher_dernier_mois:
            conditions &= Q(horodatage__date__gte=datetime.date.today() - datetime.timedelta(days=10))
        return Historique.objects.select_related("famille", "individu", "utilisateur").filter(conditions, self.Get_filtres("Q"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_dernier_mois'] = self.afficher_dernier_mois
        return context

    class datatable_class(MyDatatable):
        filtres = ['idaction', 'titre', 'detail', 'famille__nom', 'individu__nom', "utilisateur__username", "idobjet", "objet"]
        detail = columns.TextColumn("Détail", sources=[], processor='Formate_detail')
        utilisateur = columns.TextColumn("Utilisateur", sources=["utilisateur__username"], processor='Formate_utilisateur')
        famille = columns.TextColumn("Famille", sources=["famille__nom"])
        individu = columns.TextColumn("Individu", sources=["individu__nom", "individu__prenom"], processor='Formate_individu')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ['idaction', 'horodatage', 'utilisateur', 'titre', 'detail', 'famille', 'individu', "objet", "idobjet"]
            processors = {
                'horodatage': helpers.format_date('%d/%m/%Y %H:%M'),
            }
            ordering = ['-idaction']

        def Formate_detail(self, instance, **kwargs):
            return instance.detail

        def Formate_individu(self, instance, **kwargs):
            return instance.individu.Get_nom() if instance.individu else ""

        def Formate_utilisateur(self, instance, **kwargs):
            if instance.utilisateur.categorie == "utilisateur":
                return instance.utilisateur.username if instance.utilisateur else ""
            else:
                return instance.utilisateur.famille
