# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from portail.views.base import CustomView
from django.views.generic import TemplateView
from core.models import Inscription, PortailPeriode
from django.db.models import Q
import datetime


class View(CustomView, TemplateView):
    menu_code = "portail_reservations"
    template_name = "portail/reservations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Réservations"

        # Importation des inscriptions
        conditions = Q(famille=self.request.user.famille) & Q(statut="ok") & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        conditions &= Q(activite__portail_reservations_affichage="TOUJOURS") & (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=datetime.date.today()))
        inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions)

        # Récupération des individus
        context['liste_individus'] = sorted(list(set([inscription.individu for inscription in inscriptions])), key=lambda individu: individu.prenom)

        # Récupération des activités pour chaque individu
        dict_inscriptions = {}
        liste_activites = []
        for inscription in inscriptions:
            dict_inscriptions.setdefault(inscription.individu, [])
            if inscription.activite not in dict_inscriptions[inscription.individu]:
                dict_inscriptions[inscription.individu].append(inscription.activite)
            if inscription.activite not in liste_activites:
                liste_activites.append(inscription.activite)
        for individu in context['liste_individus']:
            individu.activites = sorted(dict_inscriptions[individu], key=lambda activite: activite.nom)

        # Récupération des périodes de réservation
        conditions = Q(activite__in=liste_activites) #& Q(date_debut__gte=datetime.date.today()) ACTIVER CA APRES LES TESTS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        conditions &= (Q(affichage="TOUJOURS") | (Q(affichage="PERIODE") & Q(affichage_date_debut__gte=datetime.datetime.now()) & Q(affichage_date_fin__lte=datetime.datetime.now())))
        periodes = PortailPeriode.objects.select_related("activite").prefetch_related("categories").filter(conditions).order_by("date_debut")
        dict_periodes = {}
        for periode in periodes:
            if periode.types_categories == "TOUTES" or (periode.types_categories == "AUCUNE" and not self.request.user.famille.internet_categorie) or (periode.types_categories == "SELECTION" and self.request.user.famille.internet_categorie in periode.categories.all()):
                dict_periodes.setdefault(periode.activite, [])
                dict_periodes[periode.activite].append(periode)
        context['dict_periodes'] = dict_periodes

        return context
