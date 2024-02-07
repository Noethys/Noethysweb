# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
import datetime
from core.utils import utils_infos_individus, utils_texte, utils_conversion, utils_dates, utils_questionnaires
from core.models import Cotisation, Prestation, Ventilation, Inscription
from django.db.models import Sum
from decimal import Decimal
from cotisations.utils import utils_impression_cotisation


class Cotisations():
    def __init__(self):
        """ Récupération de toutes les données de base """
        # Récupération des questionnaires
        logger.debug("Recherche tous les questionnaires...")
        self.questionnaires = utils_questionnaires.ChampsEtReponses(categorie="famille")

    def GetDonneesImpression(self, liste_cotisations=[]):
        """ Impression des factures """
        # Récupère les prestations
        dictFacturation = {}
        prestations = Prestation.objects.values('cotisation').filter(cotisation__in=liste_cotisations).annotate(total=Sum("montant"))
        for dict_temp in prestations:
            dictFacturation[dict_temp["cotisation"]] = {"montant": dict_temp["total"], "ventilation": Decimal(0), "dateReglement": None, "modeReglement": None}
        
        # Récupère la ventilation
        ventilations = Ventilation.objects.values('prestation__cotisation', 'reglement__mode__label', 'reglement__date').filter(prestation__cotisation__in=liste_cotisations).annotate(total=Sum("montant"))
        for dict_temp in ventilations:
            IDcotisation = dict_temp["prestation__cotisation"]
            if IDcotisation in dictFacturation:
                dictFacturation[IDcotisation]["ventilation"] += dict_temp["total"]
                dictFacturation[IDcotisation]["dateReglement"] = dict_temp["reglement__date"]
                dictFacturation[IDcotisation]["modeReglement"] = dict_temp["reglement__mode__label"]

        # Recherche les cotisations
        cotisations = Cotisation.objects.select_related('famille', 'type_cotisation', 'unite_cotisation', 'individu').prefetch_related('activites').filter(pk__in=liste_cotisations)

        # Recherche les familles concernées
        liste_idfamille = [cotisation.famille_id for cotisation in cotisations]

        # Recherche les inscriptions de la période
        dict_inscriptions_periode = {}
        dict_cotisations_famille = {}
        for cotisation in cotisations:
            dict_cotisations_famille.setdefault((cotisation.famille_id, cotisation.individu_id), [])
            dict_cotisations_famille[(cotisation.famille_id, cotisation.individu_id)].append(cotisation)
        for inscription in Inscription.objects.select_related("activite").filter(famille_id__in=liste_idfamille):
            for cotisation in dict_cotisations_famille.get((inscription.famille_id, inscription.individu_id), []):
                if cotisation.date_debut <= inscription.date_debut <= cotisation.date_fin:
                    dict_inscriptions_periode.setdefault(cotisation, [])
                    dict_inscriptions_periode[cotisation].append(inscription.activite.nom)

        # Récupération des infos de base individus et familles
        logger.debug("Recherche des données utils_infos_individus...")
        self.infosIndividus = utils_infos_individus.Informations(liste_familles=liste_idfamille)

        dictDonnees = {}
        dictChampsFusion = {}
        for cotisation in cotisations:

            # Nom des titulaires de famille
            beneficiaires = ""
            rue = ""
            cp = ""
            ville = ""
            
            if cotisation.famille:
                beneficiaires = cotisation.famille.nom
                rue = cotisation.famille.rue_resid
                cp = cotisation.famille.cp_resid
                ville = cotisation.famille.ville_resid
            
            if cotisation.individu:
                beneficiaires = cotisation.individu.Get_nom()
                rue = self.infosIndividus.dictIndividus[4]["INDIVIDU_RUE"]
                cp = self.infosIndividus.dictIndividus[4]["INDIVIDU_CP"]
                ville = self.infosIndividus.dictIndividus[4]["INDIVIDU_VILLE"]

            # Famille
            if cotisation.famille:
                nomTitulaires = cotisation.famille.nom
                famille_rue = cotisation.famille.rue_resid
                famille_cp = cotisation.famille.cp_resid
                famille_ville = cotisation.famille.ville_resid
            else :
                nomTitulaires = "Famille inconnue"
                famille_rue = ""
                famille_cp = ""
                famille_ville = ""
                
            # Facturation
            montant = Decimal(0)
            ventilation = Decimal(0)
            dateReglement = None
            modeReglement = None
            
            if cotisation.pk in dictFacturation:
                montant = dictFacturation[cotisation.pk]["montant"]
                ventilation = dictFacturation[cotisation.pk]["ventilation"]
                dateReglement = dictFacturation[cotisation.pk]["dateReglement"]
                modeReglement = dictFacturation[cotisation.pk]["modeReglement"]

            solde = montant - ventilation

            # Mémorisation des données
            dictDonnee = {
                "select": True,
                "{IDCOTISATION}": str(cotisation.pk),
                "{IDTYPE_COTISATION}": str(cotisation.type_cotisation.pk),
                "{IDUNITE_COTISATION}": str(cotisation.unite_cotisation.pk),
                "{DATE_SAISIE}": utils_dates.ConvertDateToFR(cotisation.date_saisie),
                "{DATE_CREATION_CARTE}": utils_dates.ConvertDateToFR(cotisation.date_creation_carte),
                "{NUMERO_CARTE}": cotisation.numero,
                # "{IDDEPOT_COTISATION}": str(IDdepot_cotisation),
                "{DATE_DEBUT}": utils_dates.ConvertDateToFR(cotisation.date_debut),
                "{DATE_FIN}": utils_dates.ConvertDateToFR(cotisation.date_fin),
                "{NOM_TYPE_COTISATION}": cotisation.type_cotisation.nom,
                "{NOM_UNITE_COTISATION}": cotisation.unite_cotisation.nom,
                "{COTISATION_FAM_IND}": "Adhésion familiale" if cotisation.type_cotisation.type == "famille" else "Adhésion individuelle",
                "{NOM_COTISATION}": "%s - %s" % (cotisation.type_cotisation, cotisation.unite_cotisation),
                # "{NOM_DEPOT}": depotStr,
                "{MONTANT_FACTURE}": utils_texte.Formate_montant(montant),
                "{MONTANT_REGLE}": utils_texte.Formate_montant(ventilation),
                "{SOLDE_ACTUEL}": utils_texte.Formate_montant(solde),
                "{MONTANT_FACTURE_LETTRES}": utils_conversion.trad(montant).capitalize(),
                "{MONTANT_REGLE_LETTRES}": utils_conversion.trad(ventilation).capitalize(),
                "{SOLDE_ACTUEL_LETTRES}": utils_conversion.trad(solde).capitalize(),
                "{DATE_REGLEMENT}": utils_dates.ConvertDateToFR(dateReglement),
                "{MODE_REGLEMENT}": modeReglement,
                "{ACTIVITES}": ", ".join([activite.nom for activite in cotisation.activites.all()]),
                "{INSCRIPTIONS_PERIODE_LIGNE}": ", ".join(dict_inscriptions_periode.get(cotisation, [])),
                "{INSCRIPTIONS_PERIODE_PARAGRAPHE}": "\n".join(dict_inscriptions_periode.get(cotisation, [])),
                "{NOTES}": cotisation.observations if cotisation.observations else "",
                "{IDINDIVIDU}": cotisation.individu_id,
                "{BENEFICIAIRE_NOM}":  beneficiaires,
                "{BENEFICIAIRE_RUE}": rue,
                "{BENEFICIAIRE_CP}": cp,
                "{BENEFICIAIRE_VILLE}": ville,
                "{IDFAMILLE}": str(cotisation.famille_id),
                "{FAMILLE_NOM}":  nomTitulaires,
                "{FAMILLE_RUE}": famille_rue,
                "{FAMILLE_CP}": famille_cp,
                "{FAMILLE_VILLE}": famille_ville,
                "{DATE_EDITION_COURT}": utils_dates.ConvertDateToFR(datetime.date.today()),
                "{DATE_EDITION_LONG}": utils_dates.ConvertDateToFR(datetime.date.today()),
                }
            
            # Ajoute les informations de base individus et familles
            if cotisation.individu:
                dictDonnee.update(self.infosIndividus.GetDictValeurs(mode="individu", ID=cotisation.individu_id, formatChamp=True))
            if cotisation.famille:
                dictDonnee.update(self.infosIndividus.GetDictValeurs(mode="famille", ID=cotisation.famille_id, formatChamp=True))

            # Ajoute les réponses des questionnaires
            for dictReponse in self.questionnaires.GetDonnees(cotisation.famille_id):
                dictDonnee[dictReponse["champ"]] = dictReponse["reponse"]
                if dictReponse["controle"] == "codebarres" :
                    dictDonnee["{CODEBARRES_QUESTION_%d}" % dictReponse["IDquestion"]] = dictReponse["reponse"]

            dictDonnees[cotisation.pk] = dictDonnee
            
            # Champs de fusion pour Email
            dictChampsFusion[cotisation.pk] = {}
            for key, valeur in dictDonnee.items():
                if key.startswith("{"):
                    dictChampsFusion[cotisation.pk][key] = valeur

        return dictDonnees, dictChampsFusion


    def Impression(self, liste_cotisations=[], dict_options=None, mode_email=False):
        """ Impression des cotisations """
        # Récupération des données à partir des IDcotisation
        logger.debug("Recherche des données d'impression...")
        resultat = self.GetDonneesImpression(liste_cotisations)
        if resultat == False :
            return False
        dict_cotisations, dictChampsFusion = resultat

        # Envoi par email
        noms_fichiers = {}
        if mode_email:
            logger.debug("Création des PDF des factures à l'unité...")
            impression = utils_impression_cotisation.Impression(dict_options=dict_options, IDmodele=dict_options["modele"].pk, generation_auto=False)
            for IDcotisation, dictCotisation in dict_cotisations.items():
                logger.debug("Création du PDF de la cotisation ID%d..." % IDcotisation)
                impression.Generation_document(dict_donnees={IDcotisation: dictCotisation})
                noms_fichiers[IDcotisation] = {"nom_fichier": impression.Get_nom_fichier(), "valeurs": impression.Get_champs_fusion_pour_email("cotisation", IDcotisation)}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_cotisation.Impression(dict_donnees=dict_cotisations, dict_options=dict_options, IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()

        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}
