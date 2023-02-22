# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, copy
logger = logging.getLogger(__name__)
from core.models import AttestationFiscale, Rattachement
from core.utils import utils_dates, utils_conversion, utils_impression, utils_infos_individus, utils_questionnaires, utils_texte
from facturation.utils import utils_impression_attestation_fiscale


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

    def GetListeTriee(self, dict_attestations_fiscales={}):
        """ Renvoie une liste d'attestations fiscales triées par nom de titulaires """
        liste_keys = [(dict_attestation["nom_famille"], idfamille) for idfamille, dict_attestation in dict_attestations_fiscales.items()]
        liste_keys.sort()
        liste_attestations_fiscales = [dict_attestations_fiscales[idattestation] for nom, idattestation in liste_keys]
        return liste_attestations_fiscales

    def GetDonneesImpression(self, liste_attestations_fiscales=[], dict_options=None):
        """ Impression des attestations fiscales """
        attestations_fiscales = AttestationFiscale.objects.select_related('famille', 'lot').filter(pk__in=liste_attestations_fiscales)
        if not attestations_fiscales:
            return False

        # Recherche la liste des familles concernées
        liste_idfamille = [attestation.famille_id for attestation in attestations_fiscales]

        # Récupération des infos de base familles
        logger.debug("Recherche toutes les infos utils_infos_individus...")
        infosIndividus = utils_infos_individus.Informations(liste_familles=liste_idfamille)

        # Importation des individus
        dict_individus = {rattachement.individu.pk: rattachement.individu for rattachement in Rattachement.objects.select_related("individu").filter(famille_id__in=liste_idfamille)}

        # Récupération des mots-clés par défaut
        dict_motscles_defaut = utils_impression.Get_motscles_defaut()

        dictAttestations = {}
        dictChampsFusion = {}
        for attestation in attestations_fiscales:
            dictAttestation = {
                "nom_famille": attestation.famille.nom,
                "nomSansCivilite": attestation.famille.nom,
                "{NOM_AVEC_CIVILITE}": attestation.famille.nom,
                "{NOM_SANS_CIVILITE}": attestation.famille.nom,
                "{FAMILLE_NOM}": attestation.famille.nom,
                "IDfamille": attestation.famille_id,
                "{IDFAMILLE}": attestation.famille_id,
                "{FAMILLE_RUE}": attestation.famille.rue_resid,
                "{FAMILLE_CP}": attestation.famille.cp_resid,
                "{FAMILLE_VILLE}": attestation.famille.ville_resid,
                "num_attestation": attestation.numero,
                "{NUM_ATTESTATION}": u"%06d" % attestation.numero,
                "{NOM_LOT}": attestation.lot if attestation.lot else "",
                "total_num": attestation.total,
                "{TOTAL}": utils_texte.Formate_montant(attestation.total),
                "{TOTAL_LETTRES}": utils_conversion.trad(attestation.total).strip().capitalize(),
                "num_codeBarre": "%07d" % attestation.numero,
                "numero": "Attestation fiscale n°%07d" % attestation.numero,
                "{CODEBARRES_NUM_ATTESTATION}": "AF%06d" % attestation.numero,
                "date_debut": attestation.date_debut,
                "date_fin": attestation.date_fin,
                "{DATE_DEBUT}": utils_dates.ConvertDateToFR(attestation.date_debut),
                "{DATE_FIN}": utils_dates.ConvertDateToFR(attestation.date_fin),
                "{DATE_EDITION_LONG}": utils_dates.DateComplete(attestation.date_edition),
                "{DATE_EDITION_COURT}": utils_dates.ConvertDateToFR(attestation.date_edition),
                "individus": [],
            }

            # Ajoute l'introduction
            dictAttestation["texte_introduction"] = self.RemplaceMotsCles(texte=copy.copy(dict_options["texte_introduction"]), dictValeurs=dictAttestation)

            # Ajoute le détail des individus
            for dict_individu in json.loads(attestation.detail):
                dictAttestation["individus"].append({"individu": dict_individus[dict_individu["idindividu"]], "montant": dict_individu["montant"]})

            # Ajoute les informations de base famille
            dictAttestation.update(infosIndividus.GetDictValeurs(mode="famille", ID=attestation.famille_id, formatChamp=True))

            # Champs de fusion pour Email
            dictChampsFusion[attestation.pk] = dictAttestation

            # Ajout les mots-clés par défaut
            dictAttestation.update(dict_motscles_defaut)

            # Mémorisation
            dictAttestations[attestation.pk] = dictAttestation

        if not dictAttestations:
            return False
           
        return dictAttestations, dictChampsFusion


    def Impression(self, liste_attestations_fiscales=[], dict_options=None, mode_email=False):
        """ Impression des attestations fiscales """
        logger.debug("Recherche des données d'impression...")
        resultat = self.GetDonneesImpression(liste_attestations_fiscales, dict_options)
        if resultat == False :
            return False
        dictAttestations, dictChampsFusion = resultat
        
        # Envoi par email
        noms_fichiers = {}
        if mode_email:
            logger.debug("Création des PDF des attestations à l'unité...")
            impression = utils_impression_attestation_fiscale.Impression(dict_options=dict_options, IDmodele=dict_options["modele"].pk, generation_auto=False)
            for IDattestation, dictAttestation in dictAttestations.items():
                logger.debug("Création du PDF de l'attestation fiscale ID%d..." % IDattestation)
                impression.Generation_document(dict_donnees={IDattestation: dictAttestation})
                noms_fichiers[IDattestation] = {"nom_fichier": impression.Get_nom_fichier(), "valeurs": impression.Get_champs_fusion_pour_email("attestation_fiscale", IDattestation)}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_attestation_fiscale.Impression(dict_donnees=dictAttestations, dict_options=dict_options, IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()

        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}
