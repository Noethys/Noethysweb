# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.contrib import messages
from core.models import Individu, Inscription, PortailPeriode, Ouverture, Unite, Vacance, Ferie, Activite, JOURS_COMPLETS_SEMAINE
from consommations.views.grille import Get_periode, Get_generic_data, Save_grille
from consommations.forms.appliquer_semaine_type import Formulaire as form_appliquer_semaine_type
from portail.templatetags.planning import is_modif_allowed
from portail.utils import utils_approbations
from portail.views.base import CustomView


class View(CustomView, TemplateView):
    menu_code = "portail_reservations"
    template_name = "portail/planning.html"

    def dispatch(self, request, *args, **kwargs):
        """ Vérifie si des approbations sont requises """
        if not request.user.is_authenticated:
            return redirect("portail_connexion")
        activite = Activite.objects.prefetch_related("types_consentements").get(pk=kwargs["idactivite"])
        approbations_requises = utils_approbations.Get_approbations_requises(famille=request.user.famille, activites=[activite,], idindividu=kwargs["idindividu"])
        if approbations_requises["nbre_total"] > 0:
            messages.add_message(request, messages.ERROR, "L'accès à ces réservations nécessite au moins une approbation. Veuillez valider les approbations en attente.")
            return redirect("portail_renseignements")
        return super(View, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """ Sauvegarde de la grille """
        Save_grille(request=request, donnees=json.loads(self.request.POST.get("donnees")))
        return HttpResponseRedirect(reverse_lazy("portail_reservations"))

    def test_func(self):
        """ Vérifie que l'utilisateur peut se connecter à cette page """
        if not super(View, self).test_func():
            return False
        inscription = Inscription.objects.filter(famille=self.request.user.famille, individu_id=self.kwargs.get('idindividu'))
        if not inscription:
            return False
        if not inscription.first().internet_reservations:
            return False
        if not self.request.user.famille.internet_reservations:
            return False
        periode = PortailPeriode.objects.select_related("activite").prefetch_related("categories").get(pk=self.kwargs.get('idperiode'))
        if not periode or not periode.Is_active_today():
            return False
        if not periode.Is_famille_authorized(famille=self.request.user.famille):
            return False
        return True

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Planning"
        context['form_appliquer_semaine_type'] = form_appliquer_semaine_type
        context['jours_complets_semaine'] = JOURS_COMPLETS_SEMAINE
        context['data'] = self.Get_data_planning()
        return context

    def Get_data_planning(self):
        data = {"mode": "portail", "idfamille": self.request.user.famille.pk, "consommations": {}, "prestations": {}, "memos": {}, "options": {}}
        data["dict_suppressions"] = {"consommations": [], "prestations": [], "memos": []}

        # Importation de l'individu
        individu = Individu.objects.get(pk=self.kwargs.get('idindividu'))
        data['individu'] = individu

        # Importation de la période
        periode_reservation = PortailPeriode.objects.select_related("activite").get(pk=self.kwargs.get('idperiode'))
        data['periode_reservation'] = periode_reservation

        # Dates de la période
        afficher_dates_passees = int(periode_reservation.activite.portail_afficher_dates_passees)
        if afficher_dates_passees == 9999:
            data["date_min"] = periode_reservation.date_debut
        else:
            data["date_min"] = max([periode_reservation.date_debut, datetime.date.today() - datetime.timedelta(days=afficher_dates_passees)])
        data["date_max"] = periode_reservation.date_fin
        data["selection_activite"] = periode_reservation.activite
        data["liste_vacances"] = Vacance.objects.filter(date_fin__gte=data["date_min"], date_debut__lte=data["date_max"]).order_by("date_debut")
        data["liste_feries"] = Ferie.objects.all()

        # Création des périodes à afficher
        data["periode"] = {'mode': 'dates', 'selections': {}, 'periodes': ['%s;%s' % (data["date_min"], data["date_max"])]}

        if periode_reservation.type_date == "VACANCES":
            data["periode"]["periodes"] = []
            for vacance in data["liste_vacances"]:
                vac_date_debut = vacance.date_debut if vacance.date_debut > data["date_min"] else data["date_min"]
                vac_date_fin = vacance.date_fin if vacance.date_fin < data["date_max"] else data["date_max"]
                data["periode"]["periodes"].append("%s;%s" % (vac_date_debut, vac_date_fin))

        if periode_reservation.type_date == "SCOLAIRES":
            data["periode"]["periodes"] = []
            dates_scolaires = [[data["date_min"], None]]
            for vacance in data["liste_vacances"]:
                dates_scolaires[-1][1] = vacance.date_debut - datetime.timedelta(days=1)
                if dates_scolaires[-1][1] < dates_scolaires[-1][0]:
                    dates_scolaires[-1][0] = vacance.date_fin + datetime.timedelta(days=1)
                else:
                    dates_scolaires.append([vacance.date_fin + datetime.timedelta(days=1), None])
                if dates_scolaires[-1][0] > data["date_max"]:
                    dates_scolaires.pop(-1)
                else:
                    dates_scolaires[-1][1] = data["date_max"]
            if dates_scolaires and not dates_scolaires[-1][1]:
                dates_scolaires[-1][1] = data["date_max"]
            data["periode"]["periodes"] = ["%s;%s" % (periode[0], periode[1]) for periode in dates_scolaires]

        # Créatio de la condition des périodes
        data = Get_periode(data)

        # Importation de toutes les inscriptions de l'individu
        data['liste_inscriptions'] = []
        for inscription in Inscription.objects.select_related('individu', 'activite', 'groupe', 'famille', 'categorie_tarif').filter(famille=self.request.user.famille, individu=individu, activite=periode_reservation.activite):
            if inscription.Is_inscription_in_periode(data["date_min"], data["date_max"]):
                data['liste_inscriptions'].append(inscription)

        # Incorpore les données génériques
        data.update(Get_generic_data(data))

        # Liste des dates modifiables
        data["dates_modifiables"] = [date for date in data["liste_dates"] if is_modif_allowed(date, data)]
        if data["dates_modifiables"]:
            data["date_modifiable_min"] = min(data["dates_modifiables"]) if data["dates_modifiables"] else None
            data["date_modifiable_max"] = max(data["dates_modifiables"]) if data["dates_modifiables"] else None

        # Liste des jours de la semaine modifiables
        jours = {date.weekday(): True for date in data["dates_modifiables"]}
        data["jours_semaine_modifiables"] = list(jours.keys())

        return data
