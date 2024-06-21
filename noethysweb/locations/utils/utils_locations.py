# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q
from core.utils import utils_infos_individus, utils_questionnaires
from core.models import Location
from locations.utils import utils_impression_location


class Locations():
    def __init__(self):
        """ Récupération de toutes les données de base """
        # Récupération des questionnaires
        logger.debug("Recherche tous les questionnaires...")
        self.questionnaires_familles = utils_questionnaires.ChampsEtReponses(categorie="famille")
        self.questionnaires_locations = utils_questionnaires.ChampsEtReponses(categorie="location")
        self.questionnaires_produits = utils_questionnaires.ChampsEtReponses(categorie="produit")

    def GetDonneesImpression(self, liste_locations=[]):
        """ Impression des locations """
        # Recherche les locations
        locations = Location.objects.select_related("famille", "produit", "produit__categorie").filter(pk__in=liste_locations)

        # Recherche les familles concernées
        liste_idfamille = [location.famille_id for location in locations]

        # Récupération des infos de base individus et familles
        logger.debug("Recherche des données utils_infos_individus...")
        self.infosIndividus = utils_infos_individus.Informations(liste_familles=liste_idfamille)

        dictDonnees = {}
        dictChampsFusion = {}
        for location in locations:
            dictDonnee = {
                "select": True,
                "{IDLOCATION}": str(location.pk),
                "{IDPRODUIT}": str(location.produit_id),
                "{DATE_DEBUT}": datetime.datetime.strftime(location.date_debut, "%d/%m/%Y"),
                "{DATE_FIN}": datetime.datetime.strftime(location.date_fin, "%d/%m/%Y") if location.date_fin else "",
                "{HEURE_DEBUT}": datetime.datetime.strftime(location.date_debut, "%Hh%M"),
                "{HEURE_FIN}": datetime.datetime.strftime(location.date_fin, "%Hh%M") if location.date_fin else "",
                "{NOM_PRODUIT}": location.produit.nom,
                "{NOM_CATEGORIE}": location.produit.categorie.nom,
                "{NOTES}": location.observations,
                "{IDFAMILLE}": str(location.famille_id),
                "{FAMILLE_NOM}": location.famille.nom,
                "{FAMILLE_RUE}": location.famille.rue_resid or "",
                "{FAMILLE_CP}": location.famille.cp_resid or "",
                "{FAMILLE_VILLE}": location.famille.ville_resid or "",
            }
            
            # Ajoute les informations de base individus et familles
            dictDonnee.update(self.infosIndividus.GetDictValeurs(mode="famille", ID=location.famille_id, formatChamp=True))
            
            # Ajoute les réponses des questionnaires
            questionnaires = [
                (self.questionnaires_familles, location.famille_id),
                (self.questionnaires_locations, location.pk),
                (self.questionnaires_produits, location.produit_id),
            ]
            for questionnaire, donnee in questionnaires:
                for dictReponse in questionnaire.GetDonnees(donnee):
                    dictDonnee[dictReponse["champ"]] = dictReponse["reponse"]
                    if dictReponse["controle"] == "codebarres":
                        dictDonnee["{CODEBARRES_QUESTION_%d}" % dictReponse["IDquestion"]] = dictReponse["reponse"]

            dictDonnees[location.pk] = dictDonnee
            
            # Champs de fusion pour Email
            dictChampsFusion[location.pk] = {}
            for key, valeur in dictDonnee.items():
                if key.startswith("{"):
                    dictChampsFusion[location.pk][key] = valeur

        return dictDonnees, dictChampsFusion


    def Impression(self, liste_locations=[], dict_options=None, mode_email=False):
        """ Impression des locations """
        # Récupération des données à partir des IDlocation
        logger.debug("Recherche des données d'impression...")
        resultat = self.GetDonneesImpression(liste_locations)
        if resultat == False :
            return False
        dict_locations, dictChampsFusion = resultat

        # Envoi par email
        noms_fichiers = {}
        if mode_email:
            logger.debug("Création des PDF des factures à l'unité...")
            impression = utils_impression_location.Impression(dict_options=dict_options, IDmodele=dict_options["modele"].pk, generation_auto=False)
            for IDlocation, dictLocation in dict_locations.items():
                logger.debug("Création du PDF de la location ID%d..." % IDlocation)
                impression.Generation_document(dict_donnees={IDlocation: dictLocation})
                noms_fichiers[IDlocation] = {"nom_fichier": impression.Get_nom_fichier(), "valeurs": impression.Get_champs_fusion_pour_email("location", IDlocation)}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_location.Impression(dict_donnees=dict_locations, dict_options=dict_options, IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()

        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}


def Get_stock_disponible(produit=None, date_debut=None, date_fin=None, location_exclue=None):
    """ Recherche si un produit est disponible sur une période donnée """
    if not date_debut:
        date_debut = datetime.datetime(1900, 1, 1)
    if not date_fin:
        date_fin = datetime.datetime(2999, 1, 1)

    # Recherche les locations du produit sur la période
    liste_dates = [date_debut, date_fin]
    conditions = Q(produit=produit) & Q(date_debut__lte=date_fin) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut))
    if location_exclue:
        conditions &= ~Q(pk=location_exclue.pk)
    liste_locations = Location.objects.filter(conditions)
    for location in liste_locations:
        if location.date_debut not in liste_dates and location.date_debut > date_debut:
            liste_dates.append(location.date_debut)
        if location.date_fin not in liste_dates and location.date_fin and location.date_fin < date_fin :
            liste_dates.append(location.date_fin)

    # Analyse des périodes de disponibilités
    liste_dates.sort()
    dict_periodes = {}
    for index in range(0, len(liste_dates)-1) :
        debut, fin = (liste_dates[index], liste_dates[index+1])
        disponible = produit.quantite
        loue = 0
        for location in liste_locations :
            if location.date_debut < fin and (not location.date_fin or location.date_fin > debut) :
                disponible -= location.quantite
                loue += location.quantite

        dict_periodes[(debut, fin)] = {"loue": loue, "disponible" : disponible}

    return dict_periodes

def Verifie_dispo_produit(produit=None, date_debut=None, date_fin=None, location_exclue=None):
    """ Vérifie que la quantité demandée d'un produit est disponible """
    liste_anomalies = []
    dictPeriodes = Get_stock_disponible(produit=produit, date_debut=date_debut, date_fin=date_fin, location_exclue=location_exclue)
    liste_periode_non_dispo = []
    for periode, valeurs in dictPeriodes.items():
        if valeurs["disponible"] < produit.quantite:
            debut = datetime.datetime.strftime(periode[0], "%d/%m/%Y-%Hh%M")
            fin = "Illimité" if periode[1].year == 2999 else datetime.datetime.strftime(periode[1], "%d/%m/%Y-%Hh%M")
            liste_periode_non_dispo.append("Stock disponible du %s au %s : %d produits" % (debut, fin, valeurs["disponible"]))
    if liste_periode_non_dispo:
        periode_str = "%s - %s" % (date_debut.strftime("%d/%m/%Y %H:%M:%S"), date_fin.strftime("%d/%m/%Y %H:%M:%S") if (date_fin and date_fin.year != 2999) else "Illimitée")
        liste_anomalies.append("Location du %s : Produit indisponible. %s." % (periode_str, ", ".join(liste_periode_non_dispo)))

    return liste_anomalies
