# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal, json
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.base import CustomView
from core.models import Facture, Prestation
from core.utils import utils_dates
from facturation.forms.liste_factures_detaillees import Formulaire


class Liste(CustomView, TemplateView):
    menu_code = "liste_factures_detaillees"
    template_name = "facturation/liste_factures_detaillees.html"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des factures détaillées"
        context['box_introduction'] = "Voici ci-dessous la liste des factures détaillées. Vous pouvez obtenir ici une liste de factures avec le détail des prestations contenues dans chaque facture."
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
            context["datatable"] = self.Get_resultats()
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_colonnes, liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
            "titre": "Factures détaillées",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        liste_lignes = []
        liste_colonnes = ["ID", "Numéro", "Nom de la famille", "Code comptable", "Montant", "Date d'édition", "Date de début",  "Date de fin"]

        if not parametres:
            return [], []

        # Création des filtres de sélection des factures
        conditions = Q()
        if parametres["type_selection"] == "DATE_EDITION":
            if not parametres["date_edition"]: return [], []
            periode = utils_dates.ConvertDateRangePicker(parametres["date_edition"])
            conditions = Q(date_edition__gte=periode[0], date_edition__lte=periode[0])
        if parametres["type_selection"] == "LOT":
            if not parametres["lot"]: return [], []
            conditions = Q(lot=parametres["lot"])

        # Importation des factures
        factures = Facture.objects.select_related("famille").filter(conditions).order_by("pk")
        prestations = Prestation.objects.select_related("activite").filter(facture__in=factures)
        
        # Analyse des factures
        dict_detail_factures = {}
        liste_colonnes_detail = []
        for prestation in prestations:
            if parametres["detail"] == "ACTIVITE" and prestation.activite:
                label_regroupement = prestation.activite.nom
            else:
                label_regroupement = prestation.label
            dict_detail_factures.setdefault(prestation.facture_id, {})
            dict_detail_factures[prestation.facture_id].setdefault(label_regroupement, decimal.Decimal(0))
            dict_detail_factures[prestation.facture_id][label_regroupement] += prestation.montant

            if label_regroupement not in liste_colonnes_detail:
                liste_colonnes_detail.append(label_regroupement)
        
        # Création des lignes
        for facture in factures:
            ligne = [
                facture.pk,
                str(facture.numero),
                facture.famille.nom,
                facture.famille.code_compta,
                str(facture.total),
                utils_dates.ConvertDateToFR(facture.date_edition),
                utils_dates.ConvertDateToFR(facture.date_debut),
                utils_dates.ConvertDateToFR(facture.date_fin)
            ]
            for label_regroupement in liste_colonnes_detail:
                ligne.append(str(dict_detail_factures.get(facture.pk, {}).get(label_regroupement, decimal.Decimal(0))))
            liste_lignes.append(ligne)

        # Création des colonnes de détail
        for label_regroupement in liste_colonnes_detail:
            liste_colonnes.append(label_regroupement)

        return liste_colonnes, liste_lignes
