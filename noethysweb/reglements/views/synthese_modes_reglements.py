# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from decimal import Decimal
from django.views.generic import TemplateView
from django.db.models import Q, Sum
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Activite, Ventilation, Reglement, ModeReglement
from reglements.forms.synthese_modes_reglements import Formulaire


class View(CustomView, TemplateView):
    menu_code = "synthese_modes_reglements"
    template_name = "reglements/synthese_modes_reglements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Synthèse des modes de règlements"
        context['afficher_menu_brothers'] = True
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
            "titre": "Synthèse des modes de règlements",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        # Récupération des paramètres
        date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
        param_activites = json.loads(parametres["activites"])
        if param_activites["type"] == "groupes_activites":
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

        # Analyse
        dictResultats = {}
        listeAnneesVentilation = []
        listeModes = []

        # Conditions Règlements
        conditions = Q()
        if parametres["type_reglements"] == "saisis":
            conditions &= Q(reglement__date__gte=date_debut, reglement__date__lte=date_fin)
        if parametres["type_reglements"] == "deposes":
            conditions &= Q(reglement__depot__date__gte=date_debut, reglement__depot__date__lte=date_fin)
        if parametres["type_reglements"] == "non_deposes":
            conditions &= Q(reglement__depot__isnull=True)
        if liste_activites:
            conditions &= Q(prestation__activite__in=liste_activites)
        if parametres["ventilation"]:
            date_debut_ventilation = utils_dates.ConvertDateENGtoDate(parametres["ventilation"].split(";")[0])
            date_fin_ventilation = utils_dates.ConvertDateENGtoDate(parametres["ventilation"].split(";")[1])
            conditions &= Q(prestation__date__gte=date_debut_ventilation, prestation__date__lte=date_fin_ventilation)

        ventilations = Ventilation.objects.select_related('prestation', 'reglement').filter(conditions, prestation__categorie__in=parametres["types_prestations"])
        listeAnneesVentilation = []
        for ventilation in ventilations:
            if ventilation.prestation.date.year not in listeAnneesVentilation:
                listeAnneesVentilation.append(ventilation.prestation.date.year)

            # Mémorisation
            IDactivite = ventilation.prestation.activite_id
            if ventilation.prestation.categorie == "cotisation":
                IDactivite = 99999

            if (IDactivite in dictResultats) == False:
                dictResultats[IDactivite] = {}
            if (ventilation.prestation.label in dictResultats[IDactivite]) == False:
                dictResultats[IDactivite][ventilation.prestation.label] = {}
            if (ventilation.reglement.mode_id in dictResultats[IDactivite][ventilation.prestation.label]) == False:
                dictResultats[IDactivite][ventilation.prestation.label][ventilation.reglement.mode_id] = Decimal(0)
            dictResultats[IDactivite][ventilation.prestation.label][ventilation.reglement.mode_id] += ventilation.montant

            if ventilation.reglement.mode_id not in listeModes:
                listeModes.append(ventilation.reglement.mode_id)

        # Recherche des règlements non ventilés
        if "avoir" in parametres["types_prestations"] and not parametres["ventilation"]:

            conditions = Q()
            if parametres["type_reglements"] == "saisis": conditions &= Q(date__gte=date_debut, date__lte=date_fin)
            if parametres["type_reglements"] == "deposes": conditions &= Q(depot__date__gte=date_debut, depot__date__lte=date_fin)
            if parametres["type_reglements"] == "non_deposes": conditions &= Q(depot__isnull=True)
            reglements = Reglement.objects.values('mode').filter(conditions).annotate(total=Sum("montant"))

            conditions = Q()
            if parametres["type_reglements"] == "saisis": conditions &= Q(reglement__date__gte=date_debut, reglement__date__lte=date_fin)
            if parametres["type_reglements"] == "deposes": conditions &= Q(reglement__depot__date__gte=date_debut, reglement__depot__date__lte=date_fin)
            if parametres["type_reglements"] == "non_deposes": conditions &= Q(reglement__depot__isnull=True)
            ventilations = Ventilation.objects.select_related('reglement').values('reglement__mode').filter(conditions).annotate(total=Sum("montant"))

            dictTemp = {}
            for ventilation in ventilations:
                dictTemp[ventilation["reglement__mode"]] = ventilation["total"]

            # Synthèse des non ventilés
            for reglement in reglements:
                IDmode = reglement["mode"]
                montant = reglement["total"]

                if IDmode in dictTemp:
                    montantAvoir = montant - dictTemp[IDmode]
                else:
                    montantAvoir = montant

                if montantAvoir > Decimal(0):
                    if (88888 in dictResultats) == False:
                        dictResultats[88888] = {"Avoirs": {}}
                    if (IDmode in dictResultats[88888]["Avoirs"]) == False:
                        dictResultats[88888]["Avoirs"][IDmode] = Decimal(0)
                    dictResultats[88888]["Avoirs"][IDmode] += montantAvoir

                    if IDmode not in listeModes:
                        listeModes.append(IDmode)


        # Remplissage
        liste_colonnes = []
        liste_lignes = []

        # Tri des modes par ordre alphabétique
        dictModes = {mode.pk: mode.label for mode in ModeReglement.objects.all()}
        listeModesAlpha = []
        for IDmode in listeModes:
            if IDmode in dictModes:
                label = dictModes[IDmode]
            else:
                label = "Mode inconnu"
            listeModesAlpha.append((label, IDmode))
        listeModesAlpha.sort()

        # Création des colonnes
        dictColonnes = {}
        liste_colonnes.append("Activités/Prestations")
        index = 1
        for IDmode in listeModes:
            liste_colonnes.append(dictModes[IDmode])
            dictColonnes[IDmode] = "col%d" % index
            index += 1
        liste_colonnes.append("Total")
        dictColonnes["total"] = "col%d" % index

        # Branches Activités
        dictActivites = {activite.pk: activite.nom for activite in Activite.objects.all()}
        listeLabels = []
        for IDactivite, dictActivite in dictResultats.items():
            if IDactivite in dictActivites:
                nomActivite = dictActivites[IDactivite]
            else:
                if IDactivite == 99999:
                    nomActivite = "Cotisations"
                elif IDactivite == 88888:
                    nomActivite = "Avoirs"
                else:
                    nomActivite = "Activité inconnue"
            listeLabels.append((nomActivite, IDactivite, dictActivite))
        listeLabels.sort()

        id_regroupement = 10000
        for nomActivite, IDactivite, dictActivite in listeLabels:
            ligne = {"id": id_regroupement, "pid": 0, "col0": nomActivite, "regroupement": True}

            # Total par mode
            dictTotal = {}
            for labelPrestation, dictPrestation in dictActivite.items():
                for IDmode, montant in dictPrestation.items():
                    if IDmode not in dictTotal:
                        dictTotal[IDmode] = Decimal(0)
                    dictTotal[IDmode] += montant

            totalLigne = Decimal(0)
            for labelMode, IDmode in listeModesAlpha:
                if IDmode in dictTotal:
                    montant = dictTotal[IDmode]
                    totalLigne += montant
                    ligne[dictColonnes[IDmode]] = float(montant)

            # Total Ligne Activité
            ligne[dictColonnes["total"]] = float(totalLigne)

            liste_lignes.append(ligne)

            # Branches Prestations
            listePrestations = []
            for labelPrestation, dictPrestation in dictActivite.items():
                listePrestations.append((labelPrestation, dictPrestation))
            listePrestations.sort()

            for labelPrestation, dictPrestation in listePrestations:
                id_detail = "detail_%s" % 0
                ligne = {"id": id_detail, "pid": id_regroupement, "col0": labelPrestation, "regroupement": False}

                # Colonnes Modes
                totalLigne = Decimal(0)
                for labelMode, IDmode in listeModesAlpha:
                    if IDmode in dictPrestation:
                        montant = dictPrestation[IDmode]
                        totalLigne += montant
                        ligne[dictColonnes[IDmode]] = float(montant)

                # Total ligne Prestation
                ligne[dictColonnes["total"]] = float(totalLigne)

                liste_lignes.append(ligne)

            id_regroupement += 1

        return liste_colonnes, liste_lignes
