# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, decimal
from django.http import Http404
from core.models import Rattachement
logger = logging.getLogger(__name__)
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from core.models import Inscription, PortailPeriode
from individus.utils import utils_familles
from portail.views.base import CustomView
from portail.utils import utils_approbations


class View(CustomView, TemplateView):
    menu_code = "portail_reservations"
    template_name = "portail/reservations.html"

    def get_object(self):
        """Récupérer l'objet famille ou individu selon l'utilisateur"""
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            return self.request.user.individu
        else:
            raise Http404("Utilisateur non reconnu.")

    def get_famille_object(self):
        """Récupérer les familles de l'individu si applicable"""
        if hasattr(self.request.user, 'famille'):
            return [self.request.user.famille]
        elif hasattr(self.request.user, 'individu'):
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            familles = [rattachement.famille for rattachement in rattachements if rattachement.famille and rattachement.titulaire == 1]
            return familles if familles else None
        return None

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Réservations")
        familles = self.get_famille_object()
        context['familles']=familles

        if familles:
            # Vérifie que la famille est autorisée à faire des réservations

            inscriptions = Inscription.objects.none()
            for famille in familles:
                # Conditions pour filtrer les inscriptions valides
                conditions = Q(famille=famille) & Q(statut="ok") & (
                            Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
                conditions &= Q(activite__portail_reservations_affichage="TOUJOURS") & (
                            Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=datetime.date.today()))
                conditions &= Q(internet_reservations=True) & Q(individu__deces=False)

                # Récupération des inscriptions valides
                inscriptions_famille = Inscription.objects.select_related("activite", "individu").filter(
                    conditions).exclude(individu__in=famille.individus_masques.all())
                inscriptions = inscriptions.union(inscriptions_famille)
                # Trier les individus par prénom
                # Récupération des individus par famille
                individus_famille = sorted(
                    set(inscription.individu for inscription in inscriptions),
                    key=lambda individu: individu.prenom
                )
                # Groupement des inscriptions par famille
                reservations_par_famille = {}

                # Récupération des activités pour chaque individu
                dict_inscriptions = {}
                liste_activites = []

                for inscription in inscriptions:
                    # Créer un ensemble de réservations pour chaque famille s'il n'existe pas
                    if inscription.famille not in reservations_par_famille:
                        reservations_par_famille[inscription.famille] = []

                    # Ajoutez l'individu et ses activités à la famille uniquement si l'individu n'est pas déjà présent
                    if inscription.individu not in reservations_par_famille[inscription.famille]:
                        reservations_par_famille[inscription.famille].append(inscription.individu)

                    # Ajouter les activités par individu
                    dict_inscriptions.setdefault(inscription.individu, [])
                    if inscription.activite not in dict_inscriptions[inscription.individu]:
                        dict_inscriptions[inscription.individu].append(inscription.activite)
                    if inscription.activite not in liste_activites:
                        liste_activites.append(inscription.activite)

                # Trier les activités pour chaque individu
                for individu in individus_famille:
                    individu.activites = sorted(dict_inscriptions[individu], key=lambda activite: activite.nom)

                # Récupération des périodes de réservation
                conditions = Q(activite__in=liste_activites)
                conditions &= (Q(affichage="TOUJOURS") | (
                            Q(affichage="PERIODE") & Q(affichage_date_debut__lte=datetime.datetime.now()) & Q(
                        affichage_date_fin__gte=datetime.datetime.now())))
                periodes = PortailPeriode.objects.select_related("activite").prefetch_related("categories").filter(
                    conditions).order_by("date_debut")

                dict_periodes = {}
                for periode in periodes:
                    if periode.Is_famille_authorized(famille=famille):
                        dict_periodes.setdefault(periode.activite, [])
                        dict_periodes[periode.activite].append(periode)

                # Ajouter les données au contexte
                context['liste_individus'] = individus_famille
                context['reservations_par_famille'] = reservations_par_famille  # Groupement par famille
                context['dict_periodes'] = dict_periodes

                # Approbations
                approbations_requises = utils_approbations.Get_approbations_requises(famille=famille)
                context['nbre_approbations_requises'] = approbations_requises["nbre_total"]

                # Blocage si impayés
                blocage_impayes = context["parametres_portail"].get("reservations_blocage_impayes", None)
                context["blocage_impayes"] = False

                if blocage_impayes and not famille.blocage_impayes_off:
                    blocage_impayes = decimal.Decimal(blocage_impayes)
                    factures = False
                    if blocage_impayes > decimal.Decimal(10000):
                        blocage_impayes -= decimal.Decimal(10000)
                        factures = True
                    if utils_familles.Get_solde_famille(idfamille=famille.pk, date_situation=datetime.date.today(),
                                                        factures=factures) >= blocage_impayes:
                        context["blocage_impayes"] = True

        return context
