# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from django.views.generic import TemplateView
from django.db.models import Q
from core.views.base import CustomView
from core.utils import utils_dates, utils_infos_individus
from core.models import Deduction, Activite
from facturation.forms.synthese_deductions import Formulaire


class View(CustomView, TemplateView):
    menu_code = "synthese_deductions"
    template_name = "facturation/synthese_deductions.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Synthèse des déductions"
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
            "titre": "Synthèse des déductions",
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        # Récupération des paramètres
        date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])
        param_activites = json.loads(parametres["activites"])
        if param_activites["type"] == "groupes_activites":
            liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
        if param_activites["type"] == "activites":
            liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

        # Récupération des informations familiales et individuelles
        infosIndividus = utils_infos_individus.Informations(date_reference=date_debut, qf=False, inscriptions=False, messages=False, infosMedicales=False,
                                                                 cotisationsManquantes=False, piecesManquantes=False, questionnaires=True, scolarite=False)
        dictInfosFamilles = infosIndividus.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

        # Déductions
        conditions = Q(date__gte=date_debut, date__lte=date_fin)
        if parametres["inclure_sans_activite"]:
            conditions &= (Q(prestation__activite__in=liste_activites) | Q(prestation__activite__isnull=True))
        else:
            conditions &= Q(prestation__activite__in=liste_activites)
        if parametres["inclure_sans_caisse"]:
            conditions &= (Q(aide__caisse__in=parametres["caisses"]) | Q(aide__caisse__isnull=True))
        else:
            conditions &= Q(aide__caisse__in=parametres["caisses"])
        deductions = Deduction.objects.select_related("famille", "famille__caisse", "prestation", "prestation__individu", "aide").filter(conditions)

        # Calcul des données
        dictResultats = {}
        liste_prestations = []
        for deduction in deductions:
            regroupement = None

            # Recherche du regroupement
            if parametres["regroupement"] == "jour": regroupement = deduction.date
            if parametres["regroupement"] == "mois": regroupement = (deduction.date.year, deduction.date.month)
            if parametres["regroupement"] == "annee": regroupement = deduction.date.year
            if parametres["regroupement"] == "montant_deduction": regroupement = deduction.montant
            if parametres["regroupement"] == "nom_aide": regroupement = deduction.aide.nom if deduction.aide else "-"
            if parametres["regroupement"] == "nom_deduction": regroupement = deduction.label
            if parametres["regroupement"] == "ville_residence": regroupement = dictInfosFamilles[deduction.famille_id]["FAMILLE_VILLE"]
            if parametres["regroupement"] == "secteur": regroupement = dictInfosFamilles[deduction.famille_id]["FAMILLE_SECTEUR"]
            if parametres["regroupement"] == "famille": regroupement = dictInfosFamilles[deduction.famille_id]["FAMILLE_NOM"]
            if parametres["regroupement"] == "individu": regroupement = deduction.prestation.individu_id
            if parametres["regroupement"] == "regime": regroupement = dictInfosFamilles[deduction.famille_id]["FAMILLE_NOM_REGIME"]
            if parametres["regroupement"] == "caisse": regroupement = dictInfosFamilles[deduction.famille_id]["FAMILLE_NOM_CAISSE"]

            # Questionnaires
            if parametres["regroupement"].startswith("question_") and "famille" in parametres["regroupement"]:
                regroupement = dictInfosFamilles[deduction.famille_id]["QUESTION_%s" % parametres["regroupement"][17:]]

            if not regroupement:
                regroupement = "- Non renseigné -"

            # Colonne
            if deduction.prestation.label not in liste_prestations:
                liste_prestations.append(deduction.prestation.label)

            # Regroupement
            if regroupement not in dictResultats:
                dictResultats[regroupement] = {
                    "caisse": deduction.famille.caisse, "num_allocataire": deduction.famille.num_allocataire, "prestations": {},
                    "montant_initial": decimal.Decimal(0), "montant_deduction": decimal.Decimal(0),
                    "montant_final": decimal.Decimal(0), "liste_dates": [], "individu": deduction.prestation.individu.Get_nom() if deduction.prestation.individu else "-",
                    "famille": dictInfosFamilles[deduction.famille_id]["FAMILLE_NOM"], "liste_individus": [],
                    "rue_resid": deduction.famille.rue_resid, "cp_resid": deduction.famille.cp_resid, "ville_resid": deduction.famille.ville_resid,
                }
            dictResultats[regroupement]["montant_initial"] += deduction.prestation.montant_initial
            dictResultats[regroupement]["montant_deduction"] += deduction.montant
            dictResultats[regroupement]["montant_final"] += deduction.prestation.montant
            if deduction.date not in dictResultats[regroupement]["liste_dates"]:
                dictResultats[regroupement]["liste_dates"].append(deduction.date)
            if deduction.prestation.individu_id not in dictResultats[regroupement]["liste_individus"]:
                dictResultats[regroupement]["liste_individus"].append(deduction.prestation.individu_id)

            # Prestations
            if deduction.prestation.label not in dictResultats[regroupement]["prestations"]:
                dictResultats[regroupement]["prestations"][deduction.prestation.label] = {
                    "nbre": 0, "liste_dates": [], "montant_initial": deduction.prestation.montant_initial,
                    "montant_deduction": deduction.montant, "montant_final": deduction.prestation.montant,
                }
            dictResultats[regroupement]["prestations"][deduction.prestation.label]["nbre"] += 1
            if deduction.date not in dictResultats[regroupement]["prestations"][deduction.prestation.label]["liste_dates"]:
                dictResultats[regroupement]["prestations"][deduction.prestation.label]["liste_dates"].append(deduction.date)
            dictResultats[regroupement]["prestations"][deduction.prestation.label]["montant_initial"] += deduction.prestation.montant_initial
            dictResultats[regroupement]["prestations"][deduction.prestation.label]["montant_deduction"] += deduction.montant
            dictResultats[regroupement]["prestations"][deduction.prestation.label]["montant_final"] += deduction.prestation.montant

        # Création de l'affichage
        liste_colonnes_temp = [
            ("regroupement", "Regroupement"),
            ("montant_initial", "Total initial"),
            ("montant_deduction", "Total déduit"),
            ("montant_final", "Total final"),
            ("date_min", "Date min"),
            ("date_max", "Date max"),
            ("nbre_dates", "Nbre dates"),
        ]
        if parametres["regroupement"] == "individu":
            liste_colonnes_temp.insert(1, ("num_allocataire", "N° Allocataire"))
            liste_colonnes_temp.insert(1, ("famille", "Famille"))
        elif parametres["regroupement"] == "famille":
            liste_colonnes_temp.insert(1, ("num_allocataire", "N° Allocataire"))
        else:
            liste_colonnes_temp.append(("nbre_individus", "Nbre individus"))
        for label_prestation in liste_prestations:
            liste_colonnes_temp.append(("prestation", label_prestation))
        if parametres["regroupement"] in ("individu", "famille"):
            liste_colonnes_temp.insert(2, ("rue_resid", "Adresse"))
            liste_colonnes_temp.insert(2, ("cp_resid", "CP"))
            liste_colonnes_temp.insert(2, ("ville_resid", "Ville"))

        # Création des colonnes
        dict_colonnes = {}
        liste_colonnes = []
        for index, (code, label) in enumerate(liste_colonnes_temp):
            liste_colonnes.append(label)
            dict_colonnes[code] = index

        # Création des lignes
        def sortby(x):
            """ Convertit un int en str mais conserve le tri """
            if isinstance(x, int):
                x = str(x).zfill(8)
            return x

        listeRegroupement = list(dictResultats.keys())
        listeRegroupement.sort(key=sortby)

        # Création d'un tableau virtuel
        liste_lignes = []
        for num_ligne in range(0, len(listeRegroupement)):
            ligne = {}
            for num_colonne in range(0, len(dict_colonnes.keys())+1):
                ligne[str(num_colonne)] = ""
            liste_lignes.append(ligne)

        index = 0
        dictLignes = {}
        for regroupement in listeRegroupement:
            if parametres["regroupement"] == "jour": label = utils_dates.DateComplete(regroupement)
            elif parametres["regroupement"] == "mois": label = utils_dates.FormateMois(regroupement)
            elif parametres["regroupement"] == "annee": label = str(regroupement)
            elif parametres["regroupement"] == "individu": label = dictResultats[regroupement]["individu"]
            else: label = str(regroupement)
            liste_lignes[index]["0"] = label
            dictLignes[regroupement] = index
            index += 1

        # Remplissage des valeurs
        for numLigne, regroupement in enumerate(listeRegroupement):
            valeurs = dictResultats[regroupement]
            for numColonne, (code_colonne, label_colonne) in enumerate(liste_colonnes_temp):
                valeur = ""
                if code_colonne == "num_allocataire": valeur = valeurs["num_allocataire"]
                if code_colonne == "famille": valeur = valeurs["famille"]
                if code_colonne == "rue_resid": valeur = valeurs["rue_resid"]
                if code_colonne == "cp_resid": valeur = valeurs["cp_resid"]
                if code_colonne == "ville_resid": valeur = valeurs["ville_resid"]
                if code_colonne == "montant_initial": valeur = float(valeurs["montant_initial"])
                if code_colonne == "montant_deduction": valeur = float(valeurs["montant_deduction"])
                if code_colonne == "montant_final": valeur = float(valeurs["montant_final"])
                if code_colonne == "date_min": valeur = utils_dates.ConvertDateToFR(min(valeurs["liste_dates"]))
                if code_colonne == "date_max": valeur = utils_dates.ConvertDateToFR(max(valeurs["liste_dates"]))
                if code_colonne == "nbre_dates": valeur = len(valeurs["liste_dates"])
                if code_colonne == "nbre_individus": valeur = len(valeurs["liste_individus"])
                if code_colonne == "prestation":
                    try:
                        valeur = valeurs["prestations"][label_colonne]["nbre"]
                    except:
                        pass
                if not code_colonne == "regroupement":
                    liste_lignes[numLigne][str(numColonne)] = valeur

        return liste_colonnes, liste_lignes
