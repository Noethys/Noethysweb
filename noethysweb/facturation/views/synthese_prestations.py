# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from decimal import Decimal
from django.views.generic import TemplateView
from django.db.models import Q, Sum, F
from core.views.base import CustomView
from core.utils import utils_dates, utils_infos_individus
from core.models import Activite, Prestation, Ventilation, TarifLigne
from facturation.forms.synthese_prestations import Formulaire


# Regroupements nécessitant les informations individuelles ou familiales : code -> champ
KEYS_INFOS_INDIVIDU = {"ville_residence": "INDIVIDU_VILLE", "secteur": "INDIVIDU_SECTEUR", "age": "INDIVIDU_AGE_INT", "ville_naissance": "INDIVIDU_VILLE_NAISS",
                       "nom_ecole": "SCOLARITE_NOM_ECOLE", "nom_classe": "SCOLARITE_NOM_CLASSE", "nom_niveau_scolaire": "SCOLARITE_NOM_NIVEAU"}
KEYS_INFOS_FAMILLE = {"regime": "FAMILLE_NOM_REGIME", "caisse": "FAMILLE_NOM_CAISSE"}
KEYS_SCOLARITE = {"nom_ecole", "nom_classe", "nom_niveau_scolaire"}


class LignePrestation(dict):
    """ Ligne de prestation issue d'un .values(), accessible comme un objet (prestation.date, prestation.montant...) """
    __slots__ = ()
    __getattr__ = dict.__getitem__

    def Get_nom_individu(self):
        """ Equivalent de Individu.Get_nom() """
        return self["individu_nom"] + " " + self["individu_prenom"] if self["individu_prenom"] else self["individu_nom"]

    def Get_code(self, code="code_comptable"):
        """ Equivalent de Prestation.Get_code_comptable() et Get_code_analytique() """
        return self["%s_prestation" % code] or self["%s_cotisation" % code] or self["%s_activite" % code] or None


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

        jointure_multiple = False
        if parametres["type_activites"] == "SELECTION":
            if param_activites["type"] == "groupes_activites":
                condition_activites = (Q(activite__groupes_activites__in=param_activites["ids"]) | Q(activite__isnull=True))
                liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
                jointure_multiple = True
            if param_activites["type"] == "activites":
                condition_activites = (Q(activite__in=param_activites["ids"]) | Q(activite__isnull=True))
                liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
        else:
            condition_activites = Q()
            liste_activites = None

        # Paramètres
        mode_affichage = parametres["donnee_case"]
        key_colonne = parametres["donnee_colonne"]
        key_ligne1 = parametres["donnee_ligne"]
        key_ligne2 = parametres["donnee_detail"]
        keys = {key_colonne, key_ligne1, key_ligne2}

        # Récupération de la ventilation des prestations de la période
        conditions_ventilations = Q(prestation__date__gte=date_debut) & Q(prestation__date__lte=date_fin)
        if liste_activites is not None:
            conditions_ventilations &= (Q(prestation__activite__in=liste_activites) | Q(prestation__activite__isnull=True))

        if parametres["filtre_reglements_saisis"]:
            date_debut_saisie = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_saisis"].split(";")[0])
            date_fin_saisie = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_saisis"].split(";")[1])
            conditions_ventilations &= (Q(reglement__date__gte=date_debut_saisie) & Q(reglement__date__lte=date_fin_saisie))

        if parametres["filtre_reglements_deposes"]:
            date_debut_depot = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_deposes"].split(";")[0])
            date_fin_depot = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_deposes"].split(";")[1])
            conditions_ventilations &= (Q(reglement__depot__date__gte=date_debut_depot) & Q(reglement__depot__date__lte=date_fin_depot))

        dictVentilation = {item["prestation"]: item["total"] for item in Ventilation.objects.filter(conditions_ventilations).values("prestation").annotate(total=Sum("montant")).order_by()}

        # Récupération des prestations de la période (on ne joint que les tables utiles aux regroupements demandés)
        conditions_prestations = conditions_periode & condition_activites & Q(categorie__in=parametres["donnees"])
        if "_facturee" in mode_affichage:
            conditions_prestations &= Q(facture__isnull=False)
        if "_nonfacturee" in mode_affichage:
            conditions_prestations &= Q(facture__isnull=True)
        # Lecture en .values() : beaucoup plus rapide que l'instanciation de centaines de milliers d'objets Prestation
        champs_base = ("idprestation", "date", "label", "montant", "tva", "activite_id", "famille_id", "individu_id", "categorie_tarif_id")
        champs = {}
        if "activite" in keys: champs["activite_nom"] = F("activite__nom")
        if "categorie_tarif" in keys: champs["categorie_tarif_nom"] = F("categorie_tarif__nom")
        if "famille" in keys: champs["famille_nom"] = F("famille__nom")
        if "individu" in keys: champs.update(individu_nom=F("individu__nom"), individu_prenom=F("individu__prenom"))
        for code, champ_prestation in (("code_comptable", "code_compta"), ("code_analytique", "code_analytique")):
            if code in keys:
                champs.update({"%s_activite" % code: F("activite__%s" % code), "%s_cotisation" % code: F("cotisation__type_cotisation__%s" % code), "%s_prestation" % code: F(champ_prestation)})
        prestations = Prestation.objects.filter(conditions_prestations).values(*champs_base, **champs)
        if jointure_multiple:
            prestations = prestations.distinct()
        prestations = [LignePrestation(ligne) for ligne in prestations]

        # Chargement des informations individuelles et familiales : uniquement si un regroupement en a besoin,
        # et uniquement pour les familles et individus concernés par les prestations
        besoin_individus = bool(keys & KEYS_INFOS_INDIVIDU.keys()) or any(key.startswith("question_individu") for key in keys)
        besoin_familles = bool(keys & KEYS_INFOS_FAMILLE.keys()) or any(key.startswith("qf") or key.startswith("question_famille") for key in keys)
        dictInfosIndividus, dictInfosFamilles = {}, {}
        if besoin_individus or besoin_familles:
            infosIndividus = utils_infos_individus.Informations(
                date_reference=date_debut, qf=any(key.startswith("qf") for key in keys), inscriptions=False, messages=False, infosMedicales=False,
                cotisationsManquantes=False, piecesManquantes=False, cotisations=False, coordonnees=False, individus=besoin_individus,
                questionnaires=any(key.startswith("question_") for key in keys), scolarite=bool(keys & KEYS_SCOLARITE),
                liste_familles={prestation.famille_id for prestation in prestations if prestation.famille_id},
                liste_individus={prestation.individu_id for prestation in prestations if prestation.individu_id})
            dictInfosIndividus = infosIndividus.GetDictValeurs(mode="individu", ID=None, formatChamp=False)
            dictInfosFamilles = infosIndividus.GetDictValeurs(mode="famille", ID=None, formatChamp=False)

        # Récupération des tranches de QF
        liste_tranches = []
        if "qf_tarifs" in keys:
            liste_tranches = sorted({(ligne.qf_min, ligne.qf_max) for ligne in TarifLigne.objects.filter(condition_activites, qf_min__isnull=False, qf_max__isnull=False).only("qf_min", "qf_max")})

        def GetKey(prestation, key_code=""):
            key = None
            key_label = ""
            key_tri = None

            if key_code == "jour":
                key = prestation.date
                key_tri = key
                key_label = utils_dates.ConvertDateToFR(prestation.date)

            elif key_code == "mois":
                key = (prestation.date.year, prestation.date.month)
                key_tri = key
                key_label = utils_dates.FormateMois(key)

            elif key_code == "annee":
                key = prestation.date.year
                key_tri = key
                key_label = str(prestation.date.year)

            elif key_code == "label_prestation":
                key = prestation.label
                key_tri = prestation.label
                key_label = prestation.label

            elif key_code == "activite":
                key = str(prestation.activite_id)
                key_label = prestation.activite_nom if prestation.activite_id else "Activité inconnue"
                key_tri = key_label

            elif key_code == "code_comptable":
                key = prestation.Get_code("code_comptable")
                key_label = key or "Code inconnu"
                key_tri = key_label

            elif key_code == "code_analytique":
                key = prestation.Get_code("code_analytique")
                key_label = key or "Code inconnu"
                key_tri = key_label

            elif key_code == "categorie_tarif":
                key = prestation.categorie_tarif_id
                key_label = prestation.categorie_tarif_nom if prestation.categorie_tarif_id else "Sans catégorie"
                key_tri = key_label

            elif key_code == "famille":
                key = prestation.famille_id
                key_label = prestation.famille_nom if prestation.famille_id else ""
                key_tri = key_label

            elif key_code == "individu":
                key = prestation.individu_id
                key_label = prestation.Get_nom_individu() if prestation.individu_id else "Individu inconnu"
                key_tri = key_label

            elif key_code in KEYS_INFOS_INDIVIDU:
                if prestation.individu_id:
                    key = dictInfosIndividus.get(prestation.individu_id, {}).get(KEYS_INFOS_INDIVIDU[key_code])
                    key_label = str(key) if key_code == "age" else key
                    key_tri = key

            elif key_code in KEYS_INFOS_FAMILLE:
                # Correction : la clé est l'ID de la famille (et non de l'individu)
                key = dictInfosFamilles.get(prestation.famille_id, {}).get(KEYS_INFOS_FAMILLE[key_code])
                key_label = key
                key_tri = key

            # QF
            elif key_code.startswith("qf"):
                key, key_tri, key_label = (0, 0), (0, 0), "- QF inconnu -"
                qf = dictInfosFamilles.get(prestation.famille_id, {}).get("FAMILLE_QF_ACTUEL_INT")
                if qf is not None:
                    tranche = None

                    # Tranches de 100
                    if key_code == "qf_100" and 0 <= qf < 10000:
                        mini = int(qf // 100 * 100)
                        tranche = (mini, mini + 99)

                    # Tranches paramétrées
                    if key_code == "qf_tarifs":
                        for mini, maxi in liste_tranches:
                            if mini <= qf <= maxi:
                                tranche = (mini, maxi)

                    if tranche:
                        key = key_tri = tranche
                        key_label = "%s - %s" % tranche

            # Questionnaires
            elif key_code.startswith("question_") and "famille" in key_code:
                key = dictInfosFamilles.get(prestation.famille_id, {}).get("QUESTION_%s" % key_code[17:])
                key_label = str(key)
                key_tri = key_label

            elif key_code.startswith("question_") and "individu" in key_code and prestation.individu_id:
                key = dictInfosIndividus.get(prestation.individu_id, {}).get("QUESTION_%s" % key_code[18:])
                key_label = str(key)
                key_tri = key_label

            if key in ("", None):
                key = "- Autre -"
                key_label = key
                key_tri = key_label

            return key, key_label, key_tri

        def Get_montant_prestation(prestation):
            if "ht" in mode_affichage and prestation.tva:
                return round(prestation.montant / (1 + prestation.tva / Decimal(100.0)), 2)
            if "tva" in mode_affichage:
                return round(prestation.montant * prestation.tva / Decimal(100.0), 2) if prestation.tva else Decimal(0)
            return prestation.montant

        def Nouveau_total(**kwargs):
            return dict(nbre=0, facture=Decimal(0), regle=Decimal(0), impaye=Decimal(0), **kwargs)

        # Regroupement
        dictPrestations = {}
        dictLabelsRegroupements = {}
        for prestation in prestations:
            # Création des keys de regroupements
            regroupement, labelRegroupement, triRegroupement = GetKey(prestation, key_colonne)
            key1, key1_label, key1_tri = GetKey(prestation, key_ligne1)
            key2, key2_label, key2_tri = GetKey(prestation, key_ligne2)

            # Mémorisation du regroupement
            if regroupement not in dictLabelsRegroupements:
                dictLabelsRegroupements[regroupement] = labelRegroupement

            montant = Get_montant_prestation(prestation)
            regle = dictVentilation.get(prestation.idprestation)

            # Total, détail par période et détail par ligne de détail
            total = dictPrestations.get(key1)
            if total is None:
                total = dictPrestations[key1] = Nouveau_total(label=key1_label, tri=key1_tri, regroupements={})
            periode = total["regroupements"].get(regroupement)
            if periode is None:
                periode = total["regroupements"][regroupement] = Nouveau_total(key2={})
            detail = periode["key2"].get(key2)
            if detail is None:
                detail = periode["key2"][key2] = Nouveau_total(label=key2_label, tri=key2_tri)

            for niveau in (total, periode, detail):
                niveau["nbre"] += 1
                niveau["facture"] += montant
                if regle is not None:
                    niveau["regle"] += regle

        # Calcul des impayés
        for total in dictPrestations.values():
            total["impaye"] = total["regle"] - total["facture"]
            for periode in total["regroupements"].values():
                periode["impaye"] = periode["regle"] - periode["facture"]
                for detail in periode["key2"].values():
                    detail["impaye"] = detail["regle"] - detail["facture"]

        listeRegroupements = sorted(dictLabelsRegroupements.keys())

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
        listeKeys1 = sorted((dictKey1["tri"], key1, dictKey1["label"]) for key1, dictKey1 in dictPrestations.items())

        id_regroupement = 10000
        for key1_tri, key1, key1_label in listeKeys1:
            ligne = {"id": id_regroupement, "pid": 0, "col0": key1_label, "regroupement": True}
            regroupements_key1 = dictPrestations[key1]["regroupements"]

            # Colonnes périodes
            for regroupement in listeRegroupements:
                if regroupement in regroupements_key1:
                    ligne[dictColonnes[regroupement]] = float(regroupements_key1[regroupement][mode_affichage])

            # Colonne Total
            ligne[dictColonnes["total"]] = float(dictPrestations[key1][mode_affichage])
            liste_lignes.append(ligne)

            # ----------------- Branches key2 -------------
            if key_ligne2 != "":
                listeKeys2 = sorted({(dictKey2["tri"], key2, dictKey2["label"]) for periode in regroupements_key1.values() for key2, dictKey2 in periode["key2"].items()})
                for key2_tri, key2, key2_label in listeKeys2:
                    ligne = {"id": "detail_%s" % str(key2), "pid": id_regroupement, "col0": key2_label, "regroupement": False}

                    # Colonnes périodes
                    totalLigne = Decimal(0)
                    for regroupement in listeRegroupements:
                        if regroupement in regroupements_key1 and key2 in regroupements_key1[regroupement]["key2"]:
                            valeur = regroupements_key1[regroupement]["key2"][key2][mode_affichage]
                            totalLigne += valeur
                            ligne[dictColonnes[regroupement]] = float(valeur)

                    # Colonne Total
                    ligne[dictColonnes["total"]] = float(totalLigne)
                    liste_lignes.append(ligne)

            id_regroupement += 1

        return liste_colonnes, liste_lignes
