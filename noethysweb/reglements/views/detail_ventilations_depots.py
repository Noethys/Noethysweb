# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Ventilation, Depot, Activite
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
        type_prestations = parametres["type_selection"] == "PRESTATIONS"
        ventilations = Ventilation.objects.select_related("reglement", "reglement__depot", "prestation", "prestation__activite", "prestation__tarif")

        # Type DEPOTS : Récupération des dépôts puis de leurs ventilations
        if parametres["type_selection"] == "DATE_DEPOT":
            date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])
            depots = list(Depot.objects.filter(date__gte=date_debut, date__lte=date_fin).order_by("date"))

        if parametres["type_selection"] == "SELECTION":
            depots = list(parametres["depots"])

        if not type_prestations:
            ventilations = ventilations.filter(reglement__depot__in=depots).order_by("prestation__date")

        # Type PRESTATIONS : Récupération des ventilations des prestations d'une période puis de leurs dépôts
        nbre_reglements_non_deposes = 0
        if type_prestations:
            date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])
            conditions = Q(prestation__date__gte=date_debut) & Q(prestation__date__lte=date_fin)
            if parametres["filtre_activites"]:
                param_activites = json.loads(parametres["activites"])
                if param_activites["type"] == "groupes_activites":
                    conditions &= Q(prestation__activite__in=Activite.objects.filter(groupes_activites__in=param_activites["ids"]))
                elif param_activites["type"] == "activites":
                    conditions &= Q(prestation__activite__in=param_activites["ids"])
                else:
                    conditions &= Q(prestation__activite__isnull=False)
            ventilations = ventilations.filter(conditions).order_by("prestation__date")

            depots = sorted({ventilation.reglement.depot for ventilation in ventilations if ventilation.reglement.depot}, key=lambda depot: (depot.date, depot.pk))
            nbre_reglements_non_deposes = len({ventilation.reglement_id for ventilation in ventilations if not ventilation.reglement.depot})
            if nbre_reglements_non_deposes:
                depots.insert(0, None)

        dict_ventilations_depot = {}
        for ventilation in ventilations:
            dict_ventilations_depot.setdefault(ventilation.reglement.depot, [])
            dict_ventilations_depot[ventilation.reglement.depot].append(ventilation)

        def Get_nom_colonne(date):
            return date.strftime("%m/%Y" if parametres["regroupement_colonne"] == "mois" else "%Y")

        def Get_nom_prestation(ventilation):
            prestation = ventilation.prestation
            if prestation.activite and prestation.activite.nom != prestation.label:
                nom_prestation = "%s : %s" % (prestation.activite.nom, prestation.label)
            else:
                nom_prestation = prestation.label
            if parametres["afficher_code_compta_prestations"]:
                code_compta = prestation.code_compta or (prestation.tarif.code_compta if prestation.tarif else None) or prestation.Get_code_comptable()
                if code_compta:
                    nom_prestation += " - %s" % code_compta
            return nom_prestation

        # Création des colonnes
        dict_colonnes = {}
        liste_colonnes = ["Dépôt"]
        for ventilation in ventilations:
            if ventilation.prestation.date:
                nom_colonne = Get_nom_colonne(ventilation.prestation.date)
                if nom_colonne not in liste_colonnes:
                    liste_colonnes.append(nom_colonne)
                    dict_colonnes[nom_colonne] = "col%d" % (len(liste_colonnes)-1)
        if not type_prestations:
            liste_colonnes.append("Non ventilé")
            dict_colonnes["non_ventile"] = "col%d" % (len(liste_colonnes)-1)
        liste_colonnes.append("Total")
        dict_colonnes["total"] = "col%d" % (len(liste_colonnes)-1)

        # Création des lignes
        id_regroupement, id_detail = 10000, 1
        for depot in depots:

            # Ligne du dépôt
            if depot:
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
            else:
                nom_depot = "----- %d règlement%s non déposé%s -----" % (nbre_reglements_non_deposes, "s" if nbre_reglements_non_deposes > 1 else "", "s" if nbre_reglements_non_deposes > 1 else "")
            ligne_regroupement = {"id": id_regroupement, "pid": 0, "col0": nom_depot, "regroupement": parametres["afficher_detail"]}

            # Colonnes de la ligne
            total_ligne = decimal.Decimal(0)
            for nom_colonne, code_colonne in dict_colonnes.items():
                montant = decimal.Decimal(0)
                for ventilation in dict_ventilations_depot.get(depot, []):
                    if nom_colonne == Get_nom_colonne(ventilation.prestation.date):
                        montant += ventilation.montant
                if montant:
                    ligne_regroupement[code_colonne] = float(montant)
                total_ligne += montant

            montant_non_ventile = 0.0
            if type_prestations:
                ligne_regroupement[dict_colonnes["total"]] = float(total_ligne)
            else:
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
                    ligne = {"id": "detail_%d" % id_detail, "pid": id_regroupement, "col0": nom_prestation, "regroupement": False}
                    id_detail += 1

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
                    ligne = {"id": "detail_%d" % id_detail, "pid": id_regroupement, "col0": "Non ventilé", "regroupement": False, dict_colonnes["non_ventile"]: montant_non_ventile, dict_colonnes["total"]: montant_non_ventile}
                    id_detail += 1
                    liste_lignes.append(ligne)

            id_regroupement += 1

        return liste_colonnes, liste_lignes
