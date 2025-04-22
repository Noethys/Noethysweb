# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from decimal import Decimal
from django.views.generic import TemplateView
from django.db.models import Q, Sum
from core.views.base import CustomView
from core.utils import utils_dates, utils_infos_individus
from core.models import Activite, Prestation, Ventilation, TarifLigne
from facturation.forms.synthese_prestations import Formulaire


class View(CustomView, TemplateView):
    menu_code = "synthese_prestations"
    template_name = "facturation/synthese_prestations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Synthèse des prestations"
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
            "titre": "Synthèse des prestations",
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

        # Paramètres
        mode_affichage = parametres["donnee_case"]
        key_colonne = parametres["donnee_colonne"]
        key_ligne1 = parametres["donnee_ligne"]
        key_ligne2 = parametres["donnee_detail"]

        # Chargement des informations individuelles
        infosIndividus = utils_infos_individus.Informations(date_reference=date_debut, qf=True, inscriptions=True, messages=False, infosMedicales=False,
                                                            cotisationsManquantes=False, piecesManquantes=False, questionnaires=True, scolarite=True)
        dictInfosIndividus = infosIndividus.GetDictValeurs(mode="individu", ID=None, formatChamp=False)
        dictInfosFamilles = infosIndividus.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

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
        if "facturee" in mode_affichage:
            conditions_prestations &= Q(facture__isnull=False)
        if "nonfacturee" in mode_affichage:
            conditions_prestations &= Q(facture__isnull=True)
        prestations = Prestation.objects.select_related('activite', 'cotisation', 'categorie_tarif', 'famille', 'individu').filter(conditions_prestations).distinct()

        # Récupération des tranches de QF
        liste_tranches = []
        lignes_tarifs = TarifLigne.objects.filter(condition_activites, qf_min__isnull=False, qf_max__isnull=False)
        for ligne_tarif in lignes_tarifs:
            tranche = ligne_tarif.qf_min, ligne_tarif.qf_max
            if tranche not in liste_tranches:
                liste_tranches.append(tranche)
        liste_tranches.sort()

        # Regroupement
        dictPrestations = {}
        listeRegroupements = []
        dictLabelsRegroupements = {}
        for prestation in prestations:

            def GetKey(key_code=""):
                key = None
                key_label = ""
                key_tri = None

                if key_code == "jour":
                    key = prestation.date
                    key_tri = key
                    key_label = utils_dates.ConvertDateToFR(prestation.date)

                if key_code == "mois":
                    key = (prestation.date.year, prestation.date.month)
                    key_tri = key
                    key_label = utils_dates.FormateMois((prestation.date.year, prestation.date.month))

                if key_code == "annee":
                    key = prestation.date.year
                    key_tri = key
                    key_label = str(prestation.date.year)

                if key_code == "label_prestation":
                    key = prestation.label
                    key_tri = prestation.label
                    key_label = prestation.label

                if key_code == "activite":
                    key = str(prestation.activite_id)
                    if not prestation.activite_id:
                        key_label = "Activité inconnue"
                    else:
                        key_label = prestation.activite.nom
                    key_tri = key_label

                if key_code == "code_comptable":
                    code_comptable = prestation.Get_code_comptable()
                    key = code_comptable
                    if not code_comptable:
                        key_label = "Code inconnu"
                    else:
                        key_label = code_comptable
                    key_tri = key_label

                if key_code == "code_analytique":
                    code_analytique = prestation.Get_code_analytique()
                    key = code_analytique
                    if not code_analytique:
                        key_label = "Code inconnu"
                    else:
                        key_label = code_analytique
                    key_tri = key_label

                if key_code == "categorie_tarif":
                    key = prestation.categorie_tarif_id
                    if not prestation.categorie_tarif_id:
                        key_label = "Sans catégorie"
                    else:
                        key_label = prestation.categorie_tarif.nom
                    key_tri = key_label

                if key_code == "famille":
                    key = prestation.famille_id
                    key_label = prestation.famille.nom
                    key_tri = key_label

                if key_code == "individu":
                    key = prestation.individu_id
                    if not prestation.individu_id:
                        key_label = "Individu inconnu"
                    else:
                        key_label = prestation.individu.Get_nom()
                    key_tri = key_label

                if key_code == "ville_residence" and prestation.individu_id:
                    key = dictInfosIndividus[prestation.individu_id]["INDIVIDU_VILLE"]
                    key_label = key
                    key_tri = key

                if key_code == "secteur" and prestation.individu_id:
                    key = dictInfosIndividus[prestation.individu_id]["INDIVIDU_SECTEUR"]
                    key_label = key
                    key_tri = key

                if key_code == "age" and prestation.individu_id:
                    key = dictInfosIndividus[prestation.individu_id]["INDIVIDU_AGE_INT"]
                    key_label = str(key)
                    key_tri = key

                if key_code == "nom_ecole" and prestation.individu_id:
                    key = dictInfosIndividus[prestation.individu_id]["SCOLARITE_NOM_ECOLE"]
                    key_label = key
                    key_tri = key

                if key_code == "nom_classe" and prestation.individu_id:
                    key = dictInfosIndividus[prestation.individu_id]["SCOLARITE_NOM_CLASSE"]
                    key_label = key
                    key_tri = key

                if key_code == "nom_niveau_scolaire" and prestation.individu_id:
                    key = dictInfosIndividus[prestation.individu_id]["SCOLARITE_NOM_NIVEAU"]
                    key_label = key
                    key_tri = key

                if key_code == "regime":
                    key = dictInfosFamilles[prestation.individu_id]["FAMILLE_NOM_REGIME"]
                    key_label = key
                    key_tri = key

                if key_code == "caisse":
                    key = dictInfosFamilles[prestation.individu_id]["FAMILLE_NOM_CAISSE"]
                    key_label = key
                    key_tri = key

                # QF
                if key_code.startswith("qf"):
                    key, key_tri, key_label = (0, 0), (0, 0), "- QF inconnu -"
                    if "FAMILLE_QF_ACTUEL_INT" in dictInfosFamilles[prestation.famille_id]:
                        qf = dictInfosFamilles[prestation.famille_id]["FAMILLE_QF_ACTUEL_INT"]

                        # Tranches de 100
                        if key_code == "qf_100":
                            for x in range(0, 10000, 100):
                                min, max = x, x + 99
                                if min <= qf <= max:
                                    key = (min, max)
                                    key_tri = key
                                    key_label = "%s - %s" % (min, max)

                        # Tranches paramétrées
                        if key_code == "qf_tarifs":
                            for min, max in liste_tranches:
                                if min <= qf <= max:
                                    key = (min, max)
                                    key_tri = key
                                    key_label = "%s - %s" % (min, max)

                # Questionnaires
                if key_code.startswith("question_") and "famille" in key_code:
                    key = dictInfosFamilles[prestation.famille_id]["QUESTION_%s" % key_code[17:]]
                    key_label = str(key)
                    key_tri = key_label

                if key_code.startswith("question_") and "individu" in key_code and prestation.individu_id:
                    key = dictInfosIndividus[prestation.individu_id]["QUESTION_%s" % key_code[18:]]
                    key_label = str(key)
                    key_tri = key_label

                if key in ("", None):
                    key = "- Autre -"
                    key_label = key
                    key_tri = key_label

                return key, key_label, key_tri

            def Get_montant_prestation():
                if "ht" in mode_affichage and prestation.tva:
                    return round(prestation.montant / (1 + prestation.tva / Decimal(100.0)), 2)
                if "tva" in mode_affichage:
                    return round(prestation.montant * prestation.tva / Decimal(100.0), 2) if prestation.tva else Decimal(0)
                return prestation.montant

            # Création des keys de regroupements
            regroupement, labelRegroupement, triRegroupement = GetKey(key_colonne)
            key1, key1_label, key1_tri = GetKey(key_ligne1)
            key2, key2_label, key2_tri = GetKey(key_ligne2)

            # Mémorisation du regroupement
            if regroupement not in listeRegroupements:
                listeRegroupements.append(regroupement)
                dictLabelsRegroupements[regroupement] = labelRegroupement

            # Total
            if key1 not in dictPrestations:
                dictPrestations[key1] = {"label": key1_label, "tri": key1_tri, "nbre": 0, "facture": Decimal(0), "regle": Decimal(0), "impaye": Decimal(0), "regroupements": {}}
            dictPrestations[key1]["nbre"] += 1
            dictPrestations[key1]["facture"] += Get_montant_prestation()

            # Détail par période
            if regroupement not in dictPrestations[key1]["regroupements"]:
                dictPrestations[key1]["regroupements"][
                    regroupement] = {"nbre": 0, "facture": Decimal(0), "regle": Decimal(0), "impaye": Decimal(0), "key2": {}}
            dictPrestations[key1]["regroupements"][regroupement]["nbre"] += 1
            dictPrestations[key1]["regroupements"][regroupement]["facture"] += Get_montant_prestation()

            # Détail par catégorie de tarifs
            if key2 not in dictPrestations[key1]["regroupements"][regroupement]["key2"]:
                dictPrestations[key1]["regroupements"][regroupement]["key2"][key2] = {"label": key2_label, "tri": key2_tri, "nbre": 0, "facture": Decimal(0), "regle": Decimal(0), "impaye": Decimal(0)}
            dictPrestations[key1]["regroupements"][regroupement]["key2"][key2]["nbre"] += 1
            dictPrestations[key1]["regroupements"][regroupement]["key2"][key2]["facture"] += Get_montant_prestation()

            # Ajoute la ventilation
            if prestation.pk in dictVentilation:
                dictPrestations[key1]["regle"] += dictVentilation[prestation.pk]
                dictPrestations[key1]["regroupements"][regroupement]["regle"] += dictVentilation[prestation.pk]
                dictPrestations[key1]["regroupements"][regroupement]["key2"][key2]["regle"] += dictVentilation[prestation.pk]

            # Calcule les impayés
            dictPrestations[key1]["impaye"] = dictPrestations[key1]["regle"] - dictPrestations[key1]["facture"]
            dictPrestations[key1]["regroupements"][regroupement]["impaye"] = dictPrestations[key1]["regroupements"][regroupement]["regle"] - dictPrestations[key1]["regroupements"][regroupement]["facture"]
            dictPrestations[key1]["regroupements"][regroupement]["key2"][key2]["impaye"] = dictPrestations[key1]["regroupements"][regroupement]["key2"][key2]["regle"] - dictPrestations[key1]["regroupements"][regroupement]["key2"][key2]["facture"]

        listeRegroupements.sort()

        # Remplissage
        liste_colonnes = []
        liste_lignes = []

        # Création des colonnes
        liste_colonnes.append("Prestations")
        for regroupement in listeRegroupements:
            liste_colonnes.append(dictLabelsRegroupements[regroupement])
        liste_colonnes.append("Total")

        mode_affichage = mode_affichage.split("_")[0]

        # Mémorisation des colonnes
        dictColonnes = {}
        index = 1
        for regroupement in listeRegroupements:
            dictColonnes[regroupement] = "col%d" % index
            index += 1
        dictColonnes["total"] = "col%d" % index

        # ------------------ Branches key1 -----------------
        listeKeys1 = []
        for key1, dictKey1 in dictPrestations.items():
            listeKeys1.append((dictKey1["tri"], key1, dictKey1["label"]))
        listeKeys1.sort()

        id_regroupement = 10000
        for key1_tri, key1, key1_label in listeKeys1:
            # niveau1 = AppendItem(root, key1_label)
            ligne = {"id": id_regroupement, "pid": 0, "col0": key1_label, "regroupement": True}

            regroupements = list(dictPrestations[key1]["regroupements"].keys())
            regroupements.sort()

            # Colonnes périodes
            for regroupement in listeRegroupements:
                if regroupement in dictPrestations[key1]["regroupements"]:
                    valeur = dictPrestations[key1]["regroupements"][regroupement][mode_affichage]
                    ligne[dictColonnes[regroupement]] = float(valeur)


            # Colonne Total
            valeur = dictPrestations[key1][mode_affichage]
            ligne[dictColonnes["total"]] = float(valeur)

            liste_lignes.append(ligne)

            # ----------------- Branches key2 -------------

            listeKeys2 = []
            for regroupement in regroupements:
                for key2, dictKey2 in dictPrestations[key1]["regroupements"][regroupement]["key2"].items():
                    key = (dictKey2["tri"], key2, dictKey2["label"])
                    if key not in listeKeys2:
                        listeKeys2.append(key)
            listeKeys2.sort()

            if key_ligne2 != "":
                for key2_tri, key2, key2_label in listeKeys2:
                    id_detail = "detail_%s" % str(key2)
                    ligne = {"id": id_detail, "pid": id_regroupement, "col0": key2_label, "regroupement": False}

                    # Colonnes périodes
                    totalLigne = Decimal(0)
                    for regroupement in listeRegroupements:
                        if regroupement in dictPrestations[key1]["regroupements"]:
                            if key2 in dictPrestations[key1]["regroupements"][regroupement]["key2"]:
                                valeur = dictPrestations[key1]["regroupements"][regroupement]["key2"][key2][mode_affichage]
                                totalLigne += valeur
                                if key_ligne2 != "":
                                    ligne[dictColonnes[regroupement]] = float(valeur)

                    # Colonne Total
                    ligne[dictColonnes["total"]] = float(totalLigne)

                    liste_lignes.append(ligne)

            id_regroupement += 1

        return liste_colonnes, liste_lignes
