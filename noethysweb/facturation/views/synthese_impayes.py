# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from decimal import Decimal
from django.views.generic import TemplateView
from django.db.models import Q, Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Activite, Prestation, Ventilation, Famille
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

        if parametres["type_activites"] == "SELECTION":
            if param_activites["type"] == "groupes_activites":
                liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
            else:
                liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
        else:
            liste_activites = Activite.objects.all()

        # Importation des activités
        dictActivites = {activite.pk: {"nom": activite.nom, "abrege": activite.abrege} for activite in liste_activites}

        def Get_conditions_prestations(prefixe=""):
            """ Conditions de sélection des prestations (prefixe = 'prestation__' pour les appliquer aux ventilations) """
            conditions = Q(**{prefixe + "date__gte": date_debut}) & Q(**{prefixe + "date__lte": date_fin}) & Q(**{prefixe + "categorie__in": parametres["donnees"]})
            if parametres["type_activites"] == "SELECTION":
                # Filtre via une sous-requête sur les IDs d'activités : évite la jointure sur les groupes d'activités et donc le DISTINCT
                conditions &= Q(**{prefixe + "activite__in": liste_activites.values("pk")}) | Q(**{prefixe + "activite__isnull": True})
            if parametres["uniquement_prestations_facturees"]:
                conditions &= Q(**{prefixe + "facture__isnull": False}) & ~Q(**{prefixe + "facture__etat": "annulation"})
            return conditions

        # Les calculs sont regroupés directement par la base de données par famille, activité, catégorie et période
        mode_mois = parametres["regroupement_colonnes"] == "mois"
        champs_regroupement = ["famille_id", "activite_id", "categorie", "annee"] + (["mois"] if mode_mois else [])

        # Total des prestations de la période
        prestations = Prestation.objects.filter(Get_conditions_prestations()).annotate(annee=ExtractYear("date"), mois=ExtractMonth("date"))
        prestations = prestations.values(*champs_regroupement).annotate(total=Sum("montant")).order_by()

        # Total des ventilations des prestations de la période
        conditions_ventilations = Get_conditions_prestations(prefixe="prestation__")

        if parametres["filtre_reglements_saisis"]:
            date_debut_saisie = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_saisis"].split(";")[0])
            date_fin_saisie = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_saisis"].split(";")[1])
            conditions_ventilations &= (Q(reglement__date__gte=date_debut_saisie) & Q(reglement__date__lte=date_fin_saisie))

        if parametres["filtre_reglements_deposes"]:
            date_debut_depot = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_deposes"].split(";")[0])
            date_fin_depot = utils_dates.ConvertDateENGtoDate(parametres["filtre_reglements_deposes"].split(";")[1])
            conditions_ventilations &= (Q(reglement__depot__date__gte=date_debut_depot) & Q(reglement__depot__date__lte=date_fin_depot))

        champs_ventilations = ["prestation__famille_id", "prestation__activite_id", "prestation__categorie", "annee"] + (["mois"] if mode_mois else [])
        ventilations = Ventilation.objects.filter(conditions_ventilations).annotate(annee=ExtractYear("prestation__date"), mois=ExtractMonth("prestation__date"))
        ventilations = ventilations.values(*champs_ventilations).annotate(total=Sum("montant")).order_by()
        dictVentilation = {tuple(ventilation[champ] for champ in champs_ventilations): ventilation["total"] or Decimal(0) for ventilation in ventilations}

        dictResultats = {"familles": {}, "activites": {}}
        listePeriodes = []
        for ligne_prestations in prestations:
            IDfamille = ligne_prestations["famille_id"]
            cle = tuple(ligne_prestations[champ] for champ in champs_regroupement)
            periode = (ligne_prestations["annee"], ligne_prestations["mois"]) if mode_mois else ligne_prestations["annee"]

            if periode not in listePeriodes:
                listePeriodes.append(periode)

            IDactivite = ligne_prestations["activite_id"]
            if ligne_prestations["categorie"] == "location":
                IDactivite = 777777
            if ligne_prestations["categorie"] == "cotisation":
                IDactivite = 888888
            if not ligne_prestations["activite_id"]:
                IDactivite = 999999

            solde = (ligne_prestations["total"] or Decimal(0)) - dictVentilation.get(cle, Decimal(0))

            # Regroupement par activités
            dict_periode = dictResultats["activites"].setdefault(IDactivite, {"total": Decimal(0), "periodes": {}})["periodes"].setdefault(periode, {"total": Decimal(0), "familles": {}})
            dictResultats["activites"][IDactivite]["total"] += solde
            dict_periode["total"] += solde
            dict_periode["familles"][IDfamille] = dict_periode["familles"].get(IDfamille, Decimal(0)) + solde

            # Regroupement par familles
            dict_periode = dictResultats["familles"].setdefault(IDfamille, {"total": Decimal(0), "periodes": {}})["periodes"].setdefault(periode, {"total": Decimal(0), "activites": {}})
            dictResultats["familles"][IDfamille]["total"] += solde
            dict_periode["total"] += solde
            dict_periode["activites"][IDactivite] = dict_periode["activites"].get(IDactivite, Decimal(0)) + solde

        # Importation des noms des familles (values_list évite le déchiffrement des champs cryptés de la famille)
        dict_noms_familles = dict(Famille.objects.filter(pk__in=dictResultats["familles"].keys()).values_list("pk", "nom"))

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
            return dict_noms_familles.get(IDfamille) or "Famille inconnue"

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
        id_regroupement, id_detail = 10000, 0
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

                listeLabels2 = set()
                if parametres["regroupement_lignes"] == "activites":
                    for periode, dictPeriode in dictResultats["activites"][ID1]["periodes"].items():
                        for IDfamille, impayes in dictPeriode["familles"].items():
                            if impayes > Decimal(0):
                                label = GetNomFamille(IDfamille)
                                listeLabels2.add((label, IDfamille))
                else:
                    for periode, dictPeriode in dictResultats["familles"][ID1]["periodes"].items():
                        for IDactivite, impayes in dictPeriode["activites"].items():
                            if impayes > Decimal(0):
                                label = GetNomActivite(IDactivite)
                                listeLabels2.add((label, IDactivite))
                for label2, ID2 in sorted(listeLabels2):
                    id_detail += 1
                    ligne = {"id": "detail_%d" % id_detail, "pid": id_regroupement, "col0": label2, "regroupement": False}
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
