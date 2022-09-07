# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from django.views.generic import TemplateView
from core.models import Inscription, PortailPeriode
from portail.views.base import CustomView
from portail.utils import utils_approbations


class View(CustomView, TemplateView):
    menu_code = "portail_reservations"
    template_name = "portail/reservations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Réservations"

        # Vérifie que la famille est autorisée à faire des réservations
        if not self.request.user.famille.internet_reservations:
            context['liste_individus'] = []
            return context

        # Importation des inscriptions
        conditions = Q(famille=self.request.user.famille) & Q(statut="ok") & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        conditions &= Q(activite__portail_reservations_affichage="TOUJOURS") & (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=datetime.date.today()))
        conditions &= Q(internet_reservations=True) & Q(individu__deces=False)
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
        conditions = Q(activite__in=liste_activites)
        conditions &= (Q(affichage="TOUJOURS") | (Q(affichage="PERIODE") & Q(affichage_date_debut__lte=datetime.datetime.now()) & Q(affichage_date_fin__gte=datetime.datetime.now())))
        periodes = PortailPeriode.objects.select_related("activite").prefetch_related("categories").filter(conditions).order_by("date_debut")
        dict_periodes = {}
        for periode in periodes:
            if periode.Is_famille_authorized(famille=self.request.user.famille):
                dict_periodes.setdefault(periode.activite, [])
                dict_periodes[periode.activite].append(periode)
        context['dict_periodes'] = dict_periodes

        # Approbations
        approbations_requises = utils_approbations.Get_approbations_requises(famille=self.request.user.famille)
        context['nbre_approbations_requises'] = approbations_requises["nbre_total"]

        return context
