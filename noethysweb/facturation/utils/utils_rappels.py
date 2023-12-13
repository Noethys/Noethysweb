# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
import datetime
from django.db.models import Q, Sum, Min, Max
from core.models import Prestation, Ventilation, Famille, Rappel
from decimal import Decimal
from core.utils import utils_dates, utils_conversion, utils_impression, utils_infos_individus, utils_questionnaires, utils_texte
from facturation.utils import utils_impression_rappel


class Facturation():
    def __init__(self):
        """ Récupération de toutes les données de base """
        # Récupération des questionnaires
        self.questionnaires = utils_questionnaires.ChampsEtReponses(categorie="famille")

    def RemplaceMotsCles(self, texte="", dictValeurs={}):
        if texte == None :
            texte = ""
        for key, valeur, in dictValeurs.items():
            if key in texte and key.startswith("{"):
                texte = texte.replace(key, str(valeur))
        return texte

    def GetListeTriee(self, dict_rappels={}):
        """ Renvoie une liste de rappels triées par nom de titulaires """
        liste_keys = [(dict_rappel["nom_famille"], idfamille) for idfamille, dict_rappel in dict_rappels.items()]
        liste_keys.sort()
        liste_rappels = [dict_rappels[idrappel] for nom, idrappel in liste_keys]
        return liste_rappels

    def GetDonnees(self, liste_activites=[], date_reference=None, date_edition=None,
                   categories_prestations=["consommation", "cotisation", "location", "autre"], selection_familles=None):
        """ Recherche des rappels à créer """
        logger.debug("Recherche les données des rappels...")

        # Recherche des prestations de la période
        conditions = (Q(activite__in=liste_activites) | Q(activite=None)) & Q(date__lte=date_reference) & Q(categorie__in=categories_prestations)
        if selection_familles:
            if selection_familles["filtre"] == "FAMILLE":
                conditions &= Q(famille_id=selection_familles["famille"])
            if selection_familles["filtre"] == "SANS_PRESTATION":
                conditions &= Q(date__lt=selection_familles["date_debut"]) & Q(date__gt=selection_familles["date_fin"])
            if selection_familles["filtre"] == "ABSENT_LOT_FACTURES":
                conditions &= ~Q(facture__lot=selection_familles["lot_factures"])

        prestations = Prestation.objects.values('famille').filter(conditions).annotate(total=Sum("montant"), date_min=Min("date"), date_max=Max("date"))
        dict_familles = {famille.pk: famille for famille in Famille.objects.all()} #filter(pk__in=liste_idfamille)} # Modifié pour éviter bug "too many SQL variables"

        # Récupération de la ventilation
        conditions = (Q(prestation__activite__in=liste_activites) | Q(prestation__activite=None)) & Q(prestation__date__lte=date_reference)
        ventilations = Ventilation.objects.values('famille').filter(conditions).annotate(total=Sum("montant"))
        dict_ventilations = {ventilation["famille"]: ventilation["total"] for ventilation in ventilations}

        # Analyse et regroupement des données
        dictComptes = {}
        for dict_prestation in prestations:
            idfamille = dict_prestation["famille"]
            famille = dict_familles[idfamille]

            # Récupère la ventilation
            montant_ventilation = dict_ventilations.get(idfamille, Decimal(0))

            numero = 0
            solde = montant_ventilation - dict_prestation["total"]
            jours_retard = (datetime.date.today() - dict_prestation["date_max"]).days

            if solde < Decimal(0):

                dictComptes[idfamille] = {
                    "nom_famille": famille.nom,
                    "{NOM_AVEC_CIVILITE}": famille.nom,
                    "{NOM_SANS_CIVILITE}": famille.nom,
                    "{FAMILLE_NOM}": famille.nom,
                    "IDfamille": idfamille,
                    "{IDFAMILLE}": idfamille,
                    "{FAMILLE_RUE}": famille.rue_resid,
                    "{FAMILLE_CP}": famille.cp_resid,
                    "{FAMILLE_VILLE}": famille.ville_resid,
                    "num_rappel": numero,
                    "{NUM_RAPPEL}": u"%06d" % numero,
                    "{NOM_LOT}": "",
                    "solde_num": solde,
                    "jours_retard": jours_retard,
                    "solde": utils_texte.Formate_montant(solde),
                    "{SOLDE}": utils_texte.Formate_montant(solde),
                    "solde_lettres": utils_conversion.trad(solde).strip().capitalize(),
                    "{SOLDE_LETTRES}": utils_conversion.trad(solde).strip().capitalize(),
                    "select": True,
                    "num_codeBarre": "%07d" % numero,
                    "numero": "Rappel n°%07d" % numero,
                    "{CODEBARRES_NUM_RAPPEL}": "F%06d" % numero,
                    "date_min": dict_prestation["date_min"],
                    "date_max": dict_prestation["date_max"],
                    "{DATE_MIN}": utils_dates.ConvertDateToFR(dict_prestation["date_min"]),
                    "{DATE_MAX}": utils_dates.ConvertDateToFR(dict_prestation["date_max"]),
                    "{DATE_EDITION_LONG}": utils_dates.DateComplete(date_edition),
                    "{DATE_EDITION_COURT}": utils_dates.ConvertDateToFR(date_edition),
                    "liste_activites": liste_activites,
                }

                # Ajoute les réponses des questionnaires
                for dictReponse in self.questionnaires.GetDonnees(idfamille) :
                    dictComptes[idfamille][dictReponse["champ"]] = dictReponse["reponse"]
                    if dictReponse["controle"] == "codebarres":
                        dictComptes[idfamille]["{CODEBARRES_QUESTION_%d}" % dictReponse["IDquestion"]] = dictReponse["reponse"]

        return dictComptes



    def GetDonneesImpression(self, liste_rappels=[], dict_options=None):
        """ Impression des rappels """
        rappels = Rappel.objects.select_related('famille', 'lot').filter(pk__in=liste_rappels)
        if not rappels:
            return False

        # Recherche la liste des familles concernées
        liste_idfamille = [rappel.famille_id for rappel in rappels]

        # Récupération des infos de base familles
        logger.debug("Recherche toutes les infos utils_infos_individus...")
        infosIndividus = utils_infos_individus.Informations(liste_familles=liste_idfamille)

        # Récupération des mots-clés par défaut
        dict_motscles_defaut = utils_impression.Get_motscles_defaut()

        dictRappels = {}
        dictChampsFusion = {}
        for rappel in rappels:
            dictRappel = {
                "nom_famille": rappel.famille.nom,
                "nomSansCivilite": rappel.famille.nom,
                "{NOM_AVEC_CIVILITE}": rappel.famille.nom,
                "{NOM_SANS_CIVILITE}": rappel.famille.nom,
                "{FAMILLE_NOM}": rappel.famille.nom,
                "IDfamille": rappel.famille_id,
                "{IDFAMILLE}": rappel.famille_id,
                "{FAMILLE_RUE}": rappel.famille.rue_resid,
                "{FAMILLE_CP}": rappel.famille.cp_resid,
                "{FAMILLE_VILLE}": rappel.famille.ville_resid,
                "num_rappel": rappel.numero,
                "{NUM_RAPPEL}": u"%06d" % rappel.numero,
                "{NOM_LOT}": rappel.lot if rappel.lot else "",
                "solde_num": -rappel.solde,
                "jours_retard": (datetime.date.today() - rappel.date_max).days,
                "solde": utils_texte.Formate_montant(-rappel.solde),
                "{SOLDE}": utils_texte.Formate_montant(-rappel.solde),
                "{SOLDE_CHIFFRES}": utils_texte.Formate_montant(-rappel.solde),
                "solde_lettres": utils_conversion.trad(-rappel.solde).strip().capitalize(),
                "{SOLDE_LETTRES}": utils_conversion.trad(-rappel.solde).strip().capitalize(),
                "select": True,
                "num_codeBarre": "%07d" % rappel.numero,
                "numero": "Rappel n°%07d" % rappel.numero,
                "{CODEBARRES_NUM_RAPPEL}": "F%06d" % rappel.numero,
                "date_min": rappel.date_min,
                "date_max": rappel.date_max,
                "date_reference": rappel.date_reference,
                "{DATE_MIN}": utils_dates.ConvertDateToFR(rappel.date_min),
                "{DATE_MAX}": utils_dates.ConvertDateToFR(rappel.date_max),
                "{DATE_EDITION_LONG}": utils_dates.DateComplete(rappel.date_edition),
                "{DATE_EDITION_COURT}": utils_dates.ConvertDateToFR(rappel.date_edition),
            }

            # Ajoute les informations de base famille
            dictRappel.update(infosIndividus.GetDictValeurs(mode="famille", ID=rappel.famille_id, formatChamp=True))

            dictRappel["texte"] = self.RemplaceMotsCles(rappel.modele.html, dictRappel)
            dictRappel["titre"] = rappel.modele.titre

            # Champs de fusion pour Email
            dictChampsFusion[rappel.pk] = {}
            dictChampsFusion[rappel.pk]["{NUMERO_RAPPEL}"] = dictRappel["{NUM_RAPPEL}"]
            dictChampsFusion[rappel.pk]["{DATE_MIN}"] = utils_dates.ConvertDateToFR(rappel.date_min)
            dictChampsFusion[rappel.pk]["{DATE_MAX}"] = utils_dates.ConvertDateToFR(rappel.date_max)
            dictChampsFusion[rappel.pk]["{DATE_EDITION_RAPPEL}"] = utils_dates.ConvertDateToFR(rappel.date_edition)
            dictChampsFusion[rappel.pk]["{DATE_REFERENCE}"] = utils_dates.ConvertDateToFR(rappel.date_reference)
            dictChampsFusion[rappel.pk]["{SOLDE_CHIFFRES}"] = dictRappel["solde"]
            dictChampsFusion[rappel.pk]["{SOLDE_LETTRES}"] = dictRappel["{SOLDE_LETTRES}"]

            # Ajout les mots-clés par défaut
            dictRappel.update(dict_motscles_defaut)

            # Mémorisation du rappel
            dictRappels[rappel.pk] = dictRappel

        if not dictRappels:
            return False
           
        return dictRappels, dictChampsFusion


    def Impression(self, liste_rappels=[], dict_options=None, mode_email=False):
        """ Impression des rappels """
        logger.debug("Recherche des données d'impression...")
        resultat = self.GetDonneesImpression(liste_rappels, dict_options)
        if resultat == False :
            return False
        dictRappels, dictChampsFusion = resultat
        
        # Envoi par email
        noms_fichiers = {}
        if mode_email:
            logger.debug("Création des PDF des rappels à l'unité...")
            impression = utils_impression_rappel.Impression(dict_options=dict_options, IDmodele=dict_options["modele"].pk, generation_auto=False)
            for IDrappel, dictRappel in dictRappels.items():
                logger.debug("Création du PDF du rappel ID%d..." % IDrappel)
                impression.Generation_document(dict_donnees={IDrappel: dictRappel})
                noms_fichiers[IDrappel] = {"nom_fichier": impression.Get_nom_fichier(), "valeurs": impression.Get_champs_fusion_pour_email("rappel", IDrappel)}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_rappel.Impression(dict_donnees=dictRappels, dict_options=dict_options, IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()

        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}
