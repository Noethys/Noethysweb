# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.models import Vacance, Activite, Ouverture, CombiTarif, TarifLigne, Tarif, Inscription, Consommation, Quotient, \
                        Prestation, Unite, CategorieTarif, Aide, CombiAide, Deduction
from core.utils import utils_dates
from django.contrib import messages
import datetime, decimal


class Forfaits():
    def __init__(self, request=None, famille=None, activites=[], individus=[], saisie_manuelle=False, saisie_auto=True):
        self.request = request
        self.selection_famille = famille
        self.selection_activites = activites
        self.selection_individus = individus
        self.saisie_manuelle = saisie_manuelle
        self.saisie_auto = saisie_auto
        self.vacances = Vacance.objects.all()
        self.montants_a_choisir = []

        # Périodes de gestion
        # self.gestion = UTILS_Gestion.Gestion(None)

    def GetForfaits(self, masquer_forfaits_obsoletes=False):
        """ Permet d'obtenir la liste des forfaits disponibles """
        # Recherche des activités
        dict_activites = {activite.pk: activite for activite in Activite.objects.filter(pk__in=self.selection_activites)}

        # Recherche les catégories de tarifs des individus
        liste_categories_tarifs = [inscription.categorie_tarif_id for inscription in Inscription.objects.filter(individu_id__in=self.selection_individus)]

        # Recherche des ouvertures
        for ouverture in Ouverture.objects.select_related("unite").filter(activite__in=self.selection_activites):
            if not hasattr(dict_activites[ouverture.activite_id], "ouvertures"): dict_activites[ouverture.activite_id].ouvertures = []
            dict_activites[ouverture.activite_id].ouvertures.append(ouverture)

        # Recherche des tarifs
        dict_tarifs = {tarif.pk: tarif for tarif in Tarif.objects.select_related("nom_tarif").prefetch_related("categories_tarifs", "groupes").filter(activite__in=self.selection_activites, type="FORFAIT", forfait_saisie_manuelle=self.saisie_manuelle, forfait_saisie_auto=self.saisie_auto)}

        # Recherche les combinaisons d'unités
        for combi_tarif in CombiTarif.objects.prefetch_related('unites').filter(tarif__activite__in=self.selection_activites):
            if combi_tarif.tarif_id in dict_tarifs:
                if not hasattr(dict_tarifs[combi_tarif.tarif_id], "combinaisons"): dict_tarifs[combi_tarif.tarif_id].combinaisons = []
                dict_tarifs[combi_tarif.tarif_id].combinaisons.append(combi_tarif)

        # Recherche des lignes de calcul
        for ligne in TarifLigne.objects.filter(activite__in=self.selection_activites):
            if ligne.tarif_id in dict_tarifs:
                if not hasattr(dict_tarifs[ligne.tarif_id], "lignes_calcul"): dict_tarifs[ligne.tarif_id].lignes_calcul = []
                dict_tarifs[ligne.tarif_id].lignes_calcul.append(ligne)

        dict_resultats = {}
        for IDtarif, tarif in dict_tarifs.items():
            inclure = True

            # Recherche si les individus ont une catégorie de tarif commune avec celles du tarif
            if not set(liste_categories_tarifs).intersection([cat.pk for cat in tarif.categories_tarifs.all()]):
                inclure = False

            # Recherche si ce tarif a des combinaisons d'unités
            tarif.date_debut_forfait = None
            tarif.date_fin_forfait = None

            if hasattr(tarif, "combinaisons") and len(tarif.combinaisons) > 0:
                # Si combinaisons personnalisées
                liste_dates = [combinaison.date for combinaison in tarif.combinaisons if combinaison.date]
                if liste_dates:
                    tarif.date_debut_forfait, tarif.date_fin_forfait = min(liste_dates), max(liste_dates)

            if tarif.options and "calendrier" in tarif.options and hasattr(dict_activites[tarif.activite_id], "ouvertures"):
                # Si selon calendrier des ouvertures
                liste_dates = [ouverture.date for ouverture in dict_activites[tarif.activite_id].ouvertures]
                if liste_dates:
                    tarif.date_debut_forfait, tarif.date_fin_forfait = min(liste_dates), max(liste_dates)

            if masquer_forfaits_obsoletes:
                if (tarif.date_fin_forfait and tarif.date_fin_forfait < datetime.date.today()) or (tarif.date_fin and tarif.date_fin < datetime.date.today()):
                    inclure = False

            # Mémorisation de ce tarif
            if inclure:
                if tarif.activite_id not in dict_resultats: dict_resultats[tarif.activite_id] = dict_activites[tarif.activite_id]
                if not hasattr(dict_resultats[tarif.activite_id], "tarifs"): dict_resultats[tarif.activite_id].tarifs = []
                dict_resultats[tarif.activite_id].tarifs.append(tarif)

        return dict_resultats

    def Applique_forfait(self, request=None, categorie_tarif=None, selection_tarif=None, mode_inscription=False, selection_activite=None, choix_montant=None):
        """ Recherche et applique les forfaits auto à l'inscription """
        self.montants_a_choisir = []
        if request:
            self.request = request

        if type(categorie_tarif) == int :
            categorie_tarif = CategorieTarif.objects.get(pk=categorie_tarif)

        # Importation des unités
        dict_unites = {unite.pk: unite for unite in Unite.objects.filter(activite__in=self.selection_activites)}

        # Importation des quotients familiaux de la famille
        quotients = Quotient.objects.filter(famille=self.selection_famille)

        # Importation des inscriptions
        dict_inscriptions = {}
        for inscription in Inscription.objects.select_related("categorie_tarif", "groupe").filter(famille=self.selection_famille, activite__in=self.selection_activites, individu__in=self.selection_individus):
            key = (inscription.individu_id, inscription.activite_id)
            if key not in dict_inscriptions: dict_inscriptions[key] = []
            dict_inscriptions[key].append(inscription)

        dict_activites = self.GetForfaits()
        for IDindividu in self.selection_individus:
            for IDactivite, activite in dict_activites.items():
                for inscription in dict_inscriptions.get((IDindividu, IDactivite), []):
                    # Récupère la catégorie de tarif
                    if not categorie_tarif:
                        categorie_tarif = inscription.categorie_tarif

                    for tarif in getattr(activite, "tarifs", []):
                        # Conditions
                        groupes_tarif = tarif.groupes.all()
                        categories_tarif = tarif.categories_tarifs.all()
                        conditions = [
                            not groupes_tarif or inscription.groupe in groupes_tarif,
                            not categories_tarif or inscription.categorie_tarif in categories_tarif,
                            (not mode_inscription and selection_tarif == tarif.pk) or (mode_inscription and selection_activite == activite.pk and tarif.forfait_saisie_auto),
                        ]
                        if False not in conditions:
                            montant_tarif = 0.0

                            # Label personnalisé
                            label_forfait = tarif.nom_tarif.nom
                            if tarif.label_prestation == "description_tarif":
                                label_forfait = tarif.description
                            if tarif.label_prestation and tarif.label_prestation.startswith("autre:"):
                                label_forfait = tarif.label_prestation[6:]

                            # Recherche de la date de facturation
                            date_facturation = tarif.date_debut_forfait if tarif.date_debut_forfait else activite.date_debut
                            if tarif.date_facturation == "date_saisie":
                                date_facturation = datetime.date.today()
                            elif tarif.date_facturation == "date_debut_activite":
                                date_facturation = activite.date_debut
                            elif tarif.date_facturation and tarif.date_facturation.startswith("date:"):
                                date_facturation = utils_dates.ConvertDateENGtoDate(tarif.date_facturation[5:])

                            # Suppression autorisée ?
                            type_forfait = 2 if tarif.forfait_suppression_auto else 1

                            # Récupération des consommations à créer
                            liste_consommations = []
                            if tarif.options and "calendrier" in tarif.options:
                                for ouverture in getattr(activite, "ouvertures", []):
                                    if ouverture.groupe_id == inscription.groupe_id:
                                        liste_consommations.append((ouverture.date, ouverture.unite))
                            else:
                                for combinaison in getattr(tarif, "combinaisons", []):
                                    if not combinaison.groupe or combinaison.groupe_id == inscription.groupe_id:
                                        for unite in combinaison.unites.all():
                                            liste_consommations.append((combinaison.date, unite))
                            liste_consommations.sort(key=lambda x: x[0])

                            # Périodes de gestion
                            # if self.gestion.Verification("consommations", listeConsommations) == False: return False

                            # Avertissement date de facturation ancienne
                            if (datetime.date.today() - date_facturation).days > 28:
                                messages.add_message(self.request, messages.WARNING, "Attention, notez que la date de facturation du forfait '%s' est ancienne (%s)" % (label_forfait, utils_dates.ConvertDateToFR(date_facturation)))

                            # Vérifie que les dates ne sont pas déjà prises
                            if liste_consommations:
                                consommations_existantes = [(conso.date, conso.unite) for conso in Consommation.objects.select_related("unite").filter(inscription=inscription, date__gte=liste_consommations[0][0], date__lte=liste_consommations[-1][0])]
                                dates_anomalies = [conso[0] for conso in liste_consommations if conso in consommations_existantes]
                                if dates_anomalies:
                                    message = "Impossible d'appliquer le forfait '%s' car des consommations existent déjà sur les dates suivantes : %s." % (label_forfait, ", ".join([utils_dates.ConvertDateToFR(date) for date in dates_anomalies]))
                                    messages.add_message(self.request, messages.ERROR, message)
                                    return

                            # ------------------ Recherche du tarif -------------------

                            def RechercheQF():
                                # Si la famille a un QF :
                                for quotient in quotients:
                                    if quotient.date_debut <= date_facturation <= quotient.date_fin and (not tarif.type_quotient or tarif.type_quotient == quotient.type_quotient):
                                        return quotient.quotient
                                # Si la famille n'a pas de QF, on attribue le QF le plus élevé :
                                listeQF = [ligne.qf_max for ligne in tarif.lignes_calcul]
                                if listeQF:
                                    return max(listeQF)
                                return None

                            # ------------ Recherche du montant du tarif : MONTANT UNIQUE
                            if tarif.methode == "montant_unique":
                                montant_tarif = tarif.lignes_calcul[0].montant_unique

                            # ------------ Recherche du montant à appliquer : QUOTIENT FAMILIAL
                            if tarif.methode == "qf":
                                montant_tarif = 0.0
                                for ligne in tarif.lignes_calcul:
                                    montant_tarif = ligne.montant_unique
                                    QFfamille = RechercheQF()
                                    if QFfamille and ligne.qf_min <= QFfamille <= ligne.qf_max:
                                        break

                            # ------------ Recherche du montant du tarif : CHOIX (MONTANT ET LABEL SELECTIONNES PAR L'UTILISATEUR)
                            if tarif.methode == "choix":
                                if selection_tarif and choix_montant:
                                    montant_tarif = choix_montant[0]
                                    if choix_montant[1]:
                                        label_forfait = choix_montant[1]
                                else:
                                    self.montants_a_choisir.append(tarif.pk)
                                    break

                            # ------------ Déduction d'une aide journalière --------------

                            # Recherche si une aide est valable à cette date et pour cet individu et pour cette activité
                            aides = Aide.objects.filter(famille_id=inscription.famille_id, individus__pk=inscription.individu_id, activite_id=inscription.activite_id)

                            def Verification_periodes(jours_scolaires, jours_vacances, date):
                                """ Vérifie si jour est scolaire ou vacances """
                                valide = False
                                if jours_scolaires:
                                    if not utils_dates.EstEnVacances(date, self.vacances) and str(
                                            date.weekday()) in jours_scolaires:
                                        valide = True
                                if jours_vacances:
                                    if utils_dates.EstEnVacances(date, self.vacances) and str(
                                            date.weekday()) in jours_vacances:
                                        valide = True
                                return valide

                            # Regroupement des unités par date
                            dict_dates = {}
                            for date, unite in liste_consommations:
                                dict_dates[date] = [unite] if date not in dict_dates.keys() else dict_dates[date] + [unite]
                                dict_dates[date] = sorted(dict_dates[date], key=lambda x: x.pk)

                            liste_aide_retenues = []
                            for aide in aides:
                                for date, combi_date in dict_dates.items():
                                    if aide.date_debut <= date <= aide.date_fin and Verification_periodes(aide.jours_scolaires, aide.jours_vacances, date):
                                        liste_combi_valides = []

                                        # On recherche si des combinaisons sont présentes sur cette ligne
                                        for combi_aide in CombiAide.objects.prefetch_related('unites').filter(aide=aide):
                                            if combi_date == list(combi_aide.unites.all().order_by("pk")):
                                                combi_aide.nbre_max_unites = len(combi_date)
                                                liste_combi_valides.append(combi_aide)

                                        if liste_combi_valides:
                                            # Tri des combinaisons par nombre d'unités et on garde la combi qui a le plus grand nombre d'unités
                                            liste_combi_valides.sort(key=lambda combi: combi.nbre_max_unites, reverse=True)
                                            combi_retenue = liste_combi_valides[0]

                                            # Vérifie que le montant max ou le nbre de dates max n'est pas déjà atteint avant application
                                            aide_valide = True
                                            liste_aides_utilisees = []
                                            if aide.nbre_dates_max or aide.montant_max:

                                                # Recherche des déductions existantes en mémoire
                                                for detail_aide in liste_aide_retenues:
                                                    liste_aides_utilisees.append({"date": detail_aide["date"], "montant": decimal.Decimal(detail_aide["montant"])})

                                                # Recherche des déductions existantes dans la base de données
                                                for deduction in Deduction.objects.filter(famille_id=inscription.famille_id, aide=combi_retenue.aide).prefetch_related('prestation'):
                                                    liste_aides_utilisees.append({"date": deduction.date, "montant": decimal.Decimal(deduction.montant)})

                                                montant_total = decimal.Decimal(0.0)
                                                dict_dates = {}
                                                for dict_aide in liste_aides_utilisees:
                                                    montant_total += decimal.Decimal(dict_aide["montant"])
                                                    dict_dates[dict_aide["date"]] = None

                                                if aide.nbre_dates_max and (len(dict_dates.keys()) >= aide.nbre_dates_max):
                                                    messages.add_message(self.request, messages.WARNING, "Le nombre de dates max de l'aide est dépassé. Aide non appliquée.")
                                                    aide_valide = False

                                                if aide.montant_max and (montant_total + combi_retenue.montant > aide.montant_max):
                                                    messages.add_message(self.request, messages.WARNING, "Le montant max de l'aide est dépassé. Aide non appliquée.")
                                                    aide_valide = False

                                            # Mémorisation de l'aide retenue
                                            if aide_valide:
                                                liste_aide_retenues.append({"date": date, "montant": combi_retenue.montant, "aide": aide})

                            # Application de la déduction
                            montant_initial = montant_tarif
                            montant_final = montant_initial
                            for detail_aide in liste_aide_retenues:
                                montant_final = montant_final - detail_aide["montant"]

                            # Sauvegarde de la prestation
                            prestation = Prestation.objects.create(
                                famille=inscription.famille, date=date_facturation, categorie="consommation", label=label_forfait,
                                montant_initial=montant_initial, montant=montant_final, activite=activite, tarif=tarif, individu=inscription.individu,
                                forfait=type_forfait, categorie_tarif=categorie_tarif, tva=tarif.tva,
                            )

                            # Sauvegarde des déductions
                            for detail_aide in liste_aide_retenues:
                                Deduction.objects.create(
                                    date=detail_aide["date"], label=detail_aide["aide"].nom, aide_id=detail_aide["aide"].pk,
                                    famille=inscription.famille, prestation=prestation, montant=detail_aide["montant"],
                                )

                            # Sauvegarde des consommations
                            liste_ajouts = []
                            for date, unite in liste_consommations:
                                conso = Consommation(
                                    individu=inscription.individu, inscription=inscription, activite=inscription.activite, date=date,
                                    unite=unite, groupe=inscription.groupe, heure_debut=dict_unites[unite.pk].heure_debut,
                                    heure_fin=dict_unites[unite.pk].heure_fin, etat="reservation", categorie_tarif=categorie_tarif,
                                    forfait=type_forfait, prestation=prestation, date_saisie=datetime.datetime.now(),
                                )
                                liste_ajouts.append(conso)
                            Consommation.objects.bulk_create(liste_ajouts)

                            # Message
                            messages.add_message(self.request, messages.SUCCESS, "Application du forfait '%s'" % label_forfait)

        return True
