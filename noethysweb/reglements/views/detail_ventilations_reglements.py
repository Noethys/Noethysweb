# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Ventilation, Reglement
from reglements.forms.detail_ventilations_reglements import Formulaire


class View(CustomView, TemplateView):
    menu_code = "detail_ventilations_reglements"
    template_name = "reglements/synthese_modes_reglements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Détail des ventilations des règlements"
        context['afficher_menu_brothers'] = True
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
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
            "titre": "Détail des ventilations des règlements",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        reglements, liste_colonnes, liste_lignes, conditions = [], [], [], None

        # Récupération des règlements
        if parametres["type_selection"] == "DATE_SAISIE":
            date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])
            conditions = Q(date__gte=date_debut) & Q(date__lte=date_fin)

        if parametres["type_selection"] == "DATE_DEPOT":
            date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])
            conditions = Q(depot__date__gte=date_debut) & Q(depot__date__lte=date_fin)

        if parametres["type_selection"] == "FAMILLE":
            conditions = Q(famille=parametres["famille"])

        if parametres["filtre_modes"] == "SELECTION":
            conditions &= Q(mode__in=parametres["selection_modes"])

        if conditions:
            reglements = Reglement.objects.select_related("emetteur", "mode", "famille").filter(conditions).order_by("date")

        # Récupération des ventilations
        ventilations = Ventilation.objects.select_related("reglement", "reglement__depot", "prestation", "prestation__activite", "prestation__cotisation").filter(reglement__in=reglements).order_by("prestation__date")
        dict_ventilations_reglement = {}
        for ventilation in ventilations:
            dict_ventilations_reglement.setdefault(ventilation.reglement, [])
            dict_ventilations_reglement[ventilation.reglement].append(ventilation)

        def Get_nom_colonne(prestation):
            if parametres["regroupement_colonne"] == "mois":
                return prestation.date.strftime("%m/%Y")
            if parametres["regroupement_colonne"] == "annee":
                return prestation.date.strftime("%Y")
            if parametres["regroupement_colonne"] == "nom_activite":
                return prestation.activite.nom if prestation.activite else "Autre"
            if parametres["regroupement_colonne"] == "code_comptable":
                return prestation.Get_code_comptable() or "Inconnu"
            if parametres["regroupement_colonne"] == "code_analytique":
                return prestation.Get_code_analytique() or "Inconnu"
            return None

        def Get_nom_prestation(ventilation):
            if ventilation.prestation.activite and ventilation.prestation.activite.nom != ventilation.prestation.label:
                return "%s : %s" % (ventilation.prestation.activite.nom, ventilation.prestation.label)
            return ventilation.prestation.label

        # Création des colonnes
        dict_colonnes = {}
        liste_colonnes = ["Règlement"]
        for ventilation in ventilations:
            if ventilation.prestation.date:
                nom_colonne = Get_nom_colonne(ventilation.prestation)
                if nom_colonne not in liste_colonnes:
                    liste_colonnes.append(nom_colonne)
                    dict_colonnes[nom_colonne] = "col%d" % (len(liste_colonnes)-1)
        liste_colonnes.append("Non ventilé")
        dict_colonnes["non_ventile"] = "col%d" % (len(liste_colonnes)-1)
        liste_colonnes.append("Total")
        dict_colonnes["total"] = "col%d" % (len(liste_colonnes)-1)

        # Création des lignes
        id_regroupement = 10000
        for reglement in reglements:

            # Ligne du règlement
            nom_reglement = []
            if parametres["afficher_id"]: nom_reglement.append("ID%d" % reglement.pk)
            if parametres["afficher_date"]: nom_reglement.append(reglement.date.strftime("%d/%m/%Y"))
            if parametres["afficher_mode"]: nom_reglement.append(reglement.mode.label)
            if parametres["afficher_famille"]: nom_reglement.append(reglement.famille.nom)
            if parametres["afficher_montant"]: nom_reglement.append(str(reglement.montant))
            ligne_regroupement = {"id": id_regroupement, "pid": 0, "col0": " - ".join(nom_reglement), "regroupement": parametres["afficher_detail"]}

            # Colonnes de la ligne
            total_ligne = decimal.Decimal(0)
            for nom_colonne, code_colonne in dict_colonnes.items():
                montant = decimal.Decimal(0)
                for ventilation in dict_ventilations_reglement.get(reglement, []):
                    if nom_colonne == Get_nom_colonne(ventilation.prestation):
                        montant += ventilation.montant
                ligne_regroupement[code_colonne] = float(montant)
                total_ligne += montant

            montant_non_ventile = float(reglement.montant - total_ligne)
            ligne_regroupement[dict_colonnes["non_ventile"]] = montant_non_ventile
            ligne_regroupement[dict_colonnes["total"]] = float(reglement.montant)
            liste_lignes.append(ligne_regroupement)

            if parametres["afficher_detail"]:

                # Branche de la prestation
                liste_prestations = []
                for ventilation in dict_ventilations_reglement.get(reglement, []):
                    nom_prestation = Get_nom_prestation(ventilation)
                    if nom_prestation not in liste_prestations:
                        liste_prestations.append(nom_prestation)
                liste_prestations.sort()

                for nom_prestation in liste_prestations:
                    id_detail = "detail_%s" % 0
                    ligne = {"id": id_detail, "pid": id_regroupement, "col0": nom_prestation, "regroupement": False}

                    # Colonnes de la ligne
                    total_ligne = decimal.Decimal(0)
                    for nom_colonne, code_colonne in dict_colonnes.items():
                        montant = decimal.Decimal(0)
                        for ventilation in dict_ventilations_reglement.get(reglement, []):
                            if nom_colonne == Get_nom_colonne(ventilation.prestation) and nom_prestation == Get_nom_prestation(ventilation):
                                montant += ventilation.montant
                        if montant:
                            ligne[code_colonne] = float(montant)
                            total_ligne += montant
                    ligne[dict_colonnes["total"]] = float(total_ligne)
                    liste_lignes.append(ligne)

                # Ajouter une ligne non ventilé
                if montant_non_ventile:
                    ligne = {"id": "detail_%s" % 0, "pid": id_regroupement, "col0": "Non ventilé", "regroupement": False, dict_colonnes["non_ventile"]: montant_non_ventile, dict_colonnes["total"]: montant_non_ventile}
                    liste_lignes.append(ligne)

            id_regroupement += 1

        return liste_colonnes, liste_lignes
