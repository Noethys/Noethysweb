# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.db.models import Q
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Consommation, Information, Ouverture
from consommations.forms.liste_repas import Formulaire


class View(CustomView, TemplateView):
    menu_code = "liste_repas"
    template_name = "consommations/liste_repas.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des repas"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_colonnes, liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
            "titre": "Liste des repas",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        # Création des conditions de période et d'activités
        date_min = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_max = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
        param_activites = json.loads(parametres["activites"])
        conditions_periodes = Q(date__gte=date_min) & Q(date__lte=date_max)
        if param_activites["type"] == "groupes_activites":
            condition_activites = Q(activite__groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            condition_activites = Q(activite__in=param_activites["ids"])

        # Importation des ouvertures
        liste_dates = []
        liste_groupes = []
        for ouverture in Ouverture.objects.select_related("unite", "groupe").filter(conditions_periodes, condition_activites).order_by("groupe__ordre"):
            if ouverture.date not in liste_dates:
                liste_dates.append(ouverture.date)
            if ouverture.groupe not in liste_groupes:
                liste_groupes.append(ouverture.groupe)
        liste_dates.sort()

        # Importation des consommations
        liste_consommations = Consommation.objects.select_related("individu", "groupe").prefetch_related("individu__regimes_alimentaires").filter(conditions_periodes, condition_activites, unite__repas=True, etat__in=("reservation", "present"))

        # Importation des informations individuelles
        categories_informations = [int(idcategorie) for idcategorie in parametres.get("categories_informations", [])]
        dict_informations_individu = {}
        for information in Information.objects.select_related("individu").filter(categorie_id__in=categories_informations, individu_id__in=list({consommation.individu.pk: True for consommation in liste_consommations}.keys())):
            dict_informations_individu.setdefault(information.individu, [])
            dict_informations_individu[information.individu].append(information.intitule)

        # Analyse des consommations
        dict_individus_date = {}
        dict_repas = {}
        for consommation in liste_consommations:

            # Mémorisation du repas
            key = (consommation.date, consommation.groupe)
            dict_repas.setdefault(key, 0)
            dict_repas[key] += consommation.quantite or 1

            # Mémorisation des individus présents sur la date
            if consommation.individu not in dict_individus_date.get(consommation.date, []):
                dict_individus_date.setdefault(consommation.date, [])
                dict_individus_date[consommation.date].append(consommation.individu)

        # Création des colonnes
        liste_colonnes = ["Date", *[groupe.nom for groupe in liste_groupes], "Total", "Informations"]

        # Création des lignes
        liste_lignes = []
        for date in liste_dates:
            # Date
            ligne = [utils_dates.ConvertDateToFR(date)]

            # Nbre de repas
            total_ligne = 0
            for index_colonne, groupe in enumerate(liste_groupes, 1):
                nbre_repas = dict_repas.get((date, groupe), 0)
                ligne.append(nbre_repas)
                total_ligne += nbre_repas
            ligne.append(total_ligne)

            # Informations
            liste_infos = []
            for individu in dict_individus_date.get(date, []):
                infos_individu = list(dict_informations_individu.get(individu, []))
                infos_individu.extend([regime.nom for regime in individu.regimes_alimentaires.all()])
                if infos_individu:
                    liste_infos.append("<b>%s</b> : %s." % (individu.Get_nom(), ", ".join(infos_individu)))
            ligne.append("<small>%s</small>" % "<br>".join(liste_infos))

            liste_lignes.append(ligne)

        return liste_colonnes, liste_lignes
