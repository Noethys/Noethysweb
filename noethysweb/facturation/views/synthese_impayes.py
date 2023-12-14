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
from core.models import Activite, Prestation, Ventilation
from facturation.forms.synthese_impayes import Formulaire


class View(CustomView, TemplateView):
    menu_code = "synthese_impayes"
    template_name = "facturation/synthese_impayes.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Synthèse des impayés"
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
            "afficher_detail": form.cleaned_data["afficher_detail"],
            "titre": "Synthèse des impayés",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])
        param_activites = json.loads(parametres["activites"])
        conditions_periode = Q(date__gte=date_debut) & Q(date__lte=date_fin)
        if param_activites["type"] == "groupes_activites":
            condition_activites = (Q(activite__groupes_activites__in=param_activites["ids"]) | Q(activite__isnull=True))
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            condition_activites = (Q(activite__in=param_activites["ids"]) | Q(activite__isnull=True))
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

        # Importation des activités
        dictActivites = {activite.pk: {"nom": activite.nom, "abrege": activite.abrege} for activite in liste_activites}

        # Importation des prestations
        conditions_ventilations = Q(prestation__date__gte=date_debut) & Q(prestation__date__lte=date_fin) & (Q(prestation__activite__in=liste_activites) | Q(prestation__activite__isnull=True))

        if parametres["filtre_reglements_saisis"]:
            date_debut_saisie = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_saisis"].split(";")[0])
            date_fin_saisie = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_saisis"].split(";")[1])
            conditions_ventilations &= (Q(reglement__depot__date__gte=date_debut_saisie) & Q(reglement__depot__date__lte=date_fin_saisie))

        if parametres["filtre_reglements_deposes"]:
            date_debut_depot = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_deposes"].split(";")[0])
            date_fin_depot = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_deposes"].split(";")[1])
            conditions_ventilations &= (Q(reglement__date__gte=date_debut_depot) & Q(reglement__date__lte=date_fin_depot))

        # Récupèration de la ventilation des prestations de la période
        dictVentilation = {}
        ventilations = Ventilation.objects.select_related('prestation', 'reglement', 'reglement_depot').values('prestation').filter(conditions_ventilations).annotate(total=Sum("montant"))
        for ventilation in ventilations:
            dictVentilation[ventilation["prestation"]] = ventilation["total"]

        # Récupération de toutes les prestations de la période
        conditions_prestations = conditions_periode & condition_activites & Q(categorie__in=parametres["donnees"])
        prestations = Prestation.objects.select_related('famille').filter(conditions_prestations).distinct()

        dictResultats = {"familles": {}, "activites": {}}
        listePeriodes = []
        dict_noms_familles = {}
        for prestation in prestations:

            if prestation.famille_id not in dict_noms_familles:
                dict_noms_familles[prestation.famille_id] = prestation.famille.nom

            if parametres["regroupement_colonnes"] == "mois":
                periode = (prestation.date.year, prestation.date.month)
            else:
                periode = prestation.date.year

            if periode not in listePeriodes:
                listePeriodes.append(periode)

            IDactivite = prestation.activite_id
            if prestation.categorie == "location":
                IDactivite = 777777
            if prestation.categorie == "cotisation":
                IDactivite = 888888
            if not prestation.activite_id:
                IDactivite = 999999

            solde = prestation.montant - dictVentilation.get(prestation.pk, Decimal(0))

            # Regroupement par activités
            if (IDactivite in dictResultats["activites"]) == False:
                dictResultats["activites"][IDactivite] = {"total": Decimal(0), "periodes": {}}
            if (periode in dictResultats["activites"][IDactivite]["periodes"]) == False:
                dictResultats["activites"][IDactivite]["periodes"][periode] = {"total": Decimal(0), "familles": {}}
            if (prestation.famille_id in dictResultats["activites"][IDactivite]["periodes"][periode]["familles"]) == False:
                dictResultats["activites"][IDactivite]["periodes"][periode]["familles"][prestation.famille_id] = Decimal(0)

            dictResultats["activites"][IDactivite]["total"] += solde
            dictResultats["activites"][IDactivite]["periodes"][periode]["total"] += solde
            dictResultats["activites"][IDactivite]["periodes"][periode]["familles"][prestation.famille_id] += solde

            # Regroupement par familles
            if (prestation.famille_id in dictResultats["familles"]) == False:
                dictResultats["familles"][prestation.famille_id] = {"total": Decimal(0), "periodes": {}}
            if (periode in dictResultats["familles"][prestation.famille_id]["periodes"]) == False:
                dictResultats["familles"][prestation.famille_id]["periodes"][periode] = {"total": Decimal(0), "activites": {}}
            if (IDactivite in dictResultats["familles"][prestation.famille_id]["periodes"][periode]["activites"]) == False:
                dictResultats["familles"][prestation.famille_id]["periodes"][periode]["activites"][IDactivite] = Decimal(0)

            dictResultats["familles"][prestation.famille_id]["total"] += solde
            dictResultats["familles"][prestation.famille_id]["periodes"][periode]["total"] += solde
            dictResultats["familles"][prestation.famille_id]["periodes"][periode]["activites"][IDactivite] += solde

        # Remplissage
        liste_colonnes = []
        liste_lignes = []

        # Mémorisation des colonnes
        listePeriodes.sort()
        dictColonnes = {}
        index = 1
        for periode in listePeriodes:
            dictColonnes[periode] = "col%d" % index
            index += 1
        dictColonnes["total"] = "col%d" % index

        # Création des colonnes
        liste_colonnes.append("Activités" if parametres["regroupement_lignes"] == "activites" else "Familles")
        for periode in listePeriodes:
            liste_colonnes.append(utils_dates.FormateMois((periode[0], periode[1])) if parametres["regroupement_colonnes"] == "mois" else str(periode))
        liste_colonnes.append("Total")

        # Création des branches
        def GetNomActivite(IDactivite=None):
            if IDactivite in dictActivites: return dictActivites[IDactivite]["nom"]
            if IDactivite == 777777: return "Locations"
            if IDactivite == 888888: return "Cotisations"
            if IDactivite == 999999: return "Autres"
            return "Activité inconnue"

        def GetNomFamille(IDfamille=None):
            return dict_noms_familles[IDfamille]

        def GetLabels(mode="activites"):
            listeLabels = []
            if mode == "activites":
                for IDactivite, dictActivite in dictResultats["activites"].items():
                    label = GetNomActivite(IDactivite)
                    if dictActivite["total"] != Decimal(0):
                        listeLabels.append((label, IDactivite))
            else:
                for IDfamille, dictFamille in dictResultats["familles"].items():
                    label = GetNomFamille(IDfamille)
                    if dictFamille["total"] != Decimal(0):
                        listeLabels.append((label, IDfamille))
            listeLabels.sort()
            return listeLabels

        # Branches de niveau 1
        id_regroupement = 10000
        listeLabels1 = GetLabels(parametres["regroupement_lignes"])
        for label1, ID1 in listeLabels1:
            ligne = {"id": id_regroupement, "pid": 0, "col0": label1, "regroupement": True}
            if parametres["regroupement_lignes"] == "familles":
                ligne.update({"type": "famille", "IDfamille": ID1})

            # Colonnes périodes
            for periode in listePeriodes:
                if periode in dictResultats[parametres["regroupement_lignes"]][ID1]["periodes"]:
                    valeur = dictResultats[parametres["regroupement_lignes"]][ID1]["periodes"][periode]["total"]
                    ligne[dictColonnes[periode]] = float(valeur)

            # Colonne Total
            valeur = dictResultats[parametres["regroupement_lignes"]][ID1]["total"]
            ligne[dictColonnes["total"]] = float(valeur)

            liste_lignes.append(ligne)


            # ----------------- Branches de niveau 2 -------------

            if parametres["afficher_detail"]:
                if parametres["regroupement_lignes"] == "activites":
                    mode2 = "familles"
                else:
                    mode2 = "activites"

                listeLabels2 = []
                if parametres["regroupement_lignes"] == "activites":
                    for periode, dictPeriode in dictResultats["activites"][ID1]["periodes"].items():
                        for IDfamille, impayes in dictPeriode["familles"].items():
                            if impayes > Decimal(0):
                                label = GetNomFamille(IDfamille)
                                if (label, IDfamille) not in listeLabels2:
                                    listeLabels2.append((label, IDfamille))
                else:
                    for periode, dictPeriode in dictResultats["familles"][ID1]["periodes"].items():
                        for IDactivite, impayes in dictPeriode["activites"].items():
                            if impayes > Decimal(0):
                                label = GetNomActivite(IDactivite)
                                if (label, IDactivite) not in listeLabels2:
                                    listeLabels2.append((label, IDactivite))
                listeLabels2.sort()

                for label2, ID2 in listeLabels2:
                    id_detail = "detail_%d" % ID1
                    ligne = {"id": id_detail, "pid": id_regroupement, "col0": label2, "regroupement": False}
                    if parametres["regroupement_lignes"] == "activites":
                        ligne.update({"type": "famille", "IDfamille": ID2})

                    # Colonnes périodes
                    totalLigne = Decimal(0)
                    for periode in listePeriodes:
                        if periode in dictResultats[parametres["regroupement_lignes"]][ID1]["periodes"]:
                            if ID2 in dictResultats[parametres["regroupement_lignes"]][ID1]["periodes"][periode][mode2]:
                                valeur = dictResultats[parametres["regroupement_lignes"]][ID1]["periodes"][periode][mode2][ID2]
                                totalLigne += valeur
                                ligne[dictColonnes[periode]] = float(valeur)

                    # Colonne Total
                    ligne[dictColonnes["total"]] = float(totalLigne)

                    liste_lignes.append(ligne)

            id_regroupement += 1

        return liste_colonnes, liste_lignes
