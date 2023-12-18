# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Ventilation, Depot
from reglements.forms.detail_ventilations_depots import Formulaire


class View(CustomView, TemplateView):
    menu_code = "detail_ventilations_depots"
    template_name = "reglements/synthese_modes_reglements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Détail des ventilations des dépôts"
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
            "titre": "Détail des ventilations des dépôts",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        depots, liste_colonnes, liste_lignes = [], [], []

        # Récupération des dépôts
        if parametres["type_selection"] == "DATE_DEPOT":
            date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
            date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
            depots = Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("date")

        if parametres["type_selection"] == "SELECTION":
            depots = parametres["depots"]

        # Récupération des ventilations
        ventilations = Ventilation.objects.select_related("reglement", "reglement__depot", "prestation", "prestation__activite").filter(reglement__depot__in=depots).order_by("prestation__date")
        dict_ventilations_depot = {}
        for ventilation in ventilations:
            dict_ventilations_depot.setdefault(ventilation.reglement.depot, [])
            dict_ventilations_depot[ventilation.reglement.depot].append(ventilation)

        def Get_nom_colonne(date):
            return date.strftime("%m/%Y" if parametres["regroupement_colonne"] == "mois" else "%Y")

        def Get_nom_prestation(ventilation):
            if ventilation.prestation.activite and ventilation.prestation.activite.nom != ventilation.prestation.label:
                return "%s : %s" % (ventilation.prestation.activite.nom, ventilation.prestation.label)
            return ventilation.prestation.label

        # Création des colonnes
        dict_colonnes = {}
        liste_colonnes = ["Dépôt"]
        for ventilation in ventilations:
            if ventilation.prestation.date:
                nom_colonne = Get_nom_colonne(ventilation.prestation.date)
                if nom_colonne not in liste_colonnes:
                    liste_colonnes.append(nom_colonne)
                    dict_colonnes[nom_colonne] = "col%d" % (len(liste_colonnes)-1)
        liste_colonnes.append("Non ventilé")
        dict_colonnes["non_ventile"] = "col%d" % (len(liste_colonnes)-1)
        liste_colonnes.append("Total")
        dict_colonnes["total"] = "col%d" % (len(liste_colonnes)-1)

        # Création des lignes
        id_regroupement = 10000
        for depot in depots:

            # Ligne du dépôt
            nom_depot = depot.nom
            detail_nom = []
            if parametres["afficher_date_depot"]:
                detail_nom.append(depot.date.strftime("%d/%m/%Y"))
            if parametres["afficher_montant_depot"]:
                detail_nom.append(str(depot.montant or 0.0))
            if parametres["afficher_code_compta"] and depot.code_compta:
                detail_nom.append(depot.code_compta)
            if detail_nom:
                nom_depot += " (%s)" % " - ".join(detail_nom)
            ligne_regroupement = {"id": id_regroupement, "pid": 0, "col0": nom_depot, "regroupement": parametres["afficher_detail"]}

            # Colonnes de la ligne
            total_ligne = decimal.Decimal(0)
            for nom_colonne, code_colonne in dict_colonnes.items():
                montant = decimal.Decimal(0)
                for ventilation in dict_ventilations_depot.get(depot, []):
                    if nom_colonne == Get_nom_colonne(ventilation.prestation.date):
                        montant += ventilation.montant
                ligne_regroupement[code_colonne] = float(montant)
                total_ligne += montant

            montant_non_ventile = float((depot.montant or decimal.Decimal(0.0)) - total_ligne)
            ligne_regroupement[dict_colonnes["non_ventile"]] = montant_non_ventile
            ligne_regroupement[dict_colonnes["total"]] = float(depot.montant or 0.0)
            liste_lignes.append(ligne_regroupement)

            if parametres["afficher_detail"]:

                # Branche de la prestation
                liste_prestations = []
                for ventilation in dict_ventilations_depot.get(depot, []):
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
                        for ventilation in dict_ventilations_depot.get(depot, []):
                            if nom_colonne == Get_nom_colonne(ventilation.prestation.date) and nom_prestation == Get_nom_prestation(ventilation):
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
