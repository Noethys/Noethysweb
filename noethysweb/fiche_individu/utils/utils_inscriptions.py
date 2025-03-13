# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging

logger = logging.getLogger(__name__)
import datetime
from core.utils import utils_infos_individus, utils_texte, utils_conversion, utils_dates, utils_questionnaires
from core.models import Inscription
from django.db.models import Sum
from decimal import Decimal
from fiche_individu.utils import utils_impression_inscription


class Inscriptions():
    def __init__(self):
        """ Récupération de toutes les données de base """
        # Récupération des questionnaires
        logger.debug("Recherche tous les questionnaires...")
        self.questionnaires = utils_questionnaires.ChampsEtReponses(categorie="famille")

    def GetDonneesImpression(self, liste_inscriptions=[]):
        """ Impression des factures """
        logger.debug("Recherche des données d'impression...")

        # Recherche les inscriptions
        inscriptions = Inscription.objects.select_related("famille", "individu", "groupe", "categorie_tarif",
                                                          "activite").filter(pk__in=liste_inscriptions)

        # Recherche les familles concernées
        liste_idfamille = [inscription.famille_id for inscription in inscriptions]

        # Récupération des infos de base individus et familles
        logger.debug("Recherche des données utils_infos_individus...")
        infosIndividus = utils_infos_individus.Informations(liste_familles=liste_idfamille)

        dictDonnees = {}
        dictChampsFusion = {}
        for inscription in inscriptions:

            # Mémorisation des données
            dictDonnee = {
                "{IDINSCRIPTION}": str(inscription.pk),
                "{DATE_DEBUT}": utils_dates.ConvertDateToFR(inscription.date_debut),
                "{DATE_FIN}": utils_dates.ConvertDateToFR(inscription.date_fin) or "",

                "{IDINDIVIDU}": inscription.individu_id,
                "{INDIVIDU_NOM}": inscription.individu.nom,
                "{INDIVIDU_PRENOM}": inscription.individu.prenom,
                "{INDIVIDU_RUE}": inscription.individu.rue_resid,
                "{INDIVIDU_CP}": inscription.individu.cp_resid,
                "{INDIVIDU_VILLE}": inscription.individu.ville_resid,

                "{IDFAMILLE}": str(inscription.famille_id),
                "{FAMILLE_NOM}": inscription.famille.nom,
                "{FAMILLE_RUE}": inscription.famille.rue_resid,
                "{FAMILLE_CP}": inscription.famille.cp_resid,
                "{FAMILLE_VILLE}": inscription.famille.ville_resid,

                "{IDACTIVITE}": inscription.activite_id,
                "{ACTIVITE_NOM_LONG}": inscription.activite.nom,
                "{ACTIVITE_NOM_COURT}": inscription.activite.abrege,

                "{IDGROUPE}": inscription.groupe_id,
                "{GROUPE_NOM_LONG}": inscription.groupe.nom,
                "{GROUPE_NOM_COURT}": inscription.groupe.abrege,

                "{IDCATEGORIETARIF}": inscription.categorie_tarif.pk,
                "{NOM_CATEGORIE_TARIF}": inscription.categorie_tarif.nom,
            }

            # Ajoute les informations de base individus et familles
            dictDonnee.update(
                infosIndividus.GetDictValeurs(mode="famille", ID=inscription.famille_id, formatChamp=True))

            # Ajoute les réponses des questionnaires
            for dictReponse in self.questionnaires.GetDonnees(inscription.famille_id):
                dictDonnee[dictReponse["champ"]] = dictReponse["reponse"]
                if dictReponse["controle"] == "codebarres":
                    dictDonnee["{CODEBARRES_QUESTION_%d}" % dictReponse["IDquestion"]] = dictReponse["reponse"]

            dictDonnees[inscription.pk] = dictDonnee

            # Champs de fusion pour Email
            dictChampsFusion[inscription.pk] = {}
            for key, valeur in dictDonnee.items():
                if key.startswith("{"):
                    dictChampsFusion[inscription.pk][key] = valeur

        return dictDonnees, dictChampsFusion

    def Impression(self, liste_inscriptions=[], dict_options=None, mode_email=False):
        """ Impression des inscriptions """
        # Récupération des données à partir des IDinscription
        logger.debug("Recherche des données d'impression...")
        resultat = self.GetDonneesImpression(liste_inscriptions)
        if resultat == False:
            return False
        dict_inscriptions, dictChampsFusion = resultat

        # Envoi par email
        noms_fichiers = {}
        if mode_email:
            logger.debug("Création des PDF des inscriptions à l'unité...")
            if dict_options and "modele" in dict_options and dict_options["modele"]:
                IDmodele = dict_options["modele"].pk

            else:
                from core.models import ModeleDocument  # Importer si nécessaire
                modele_defaut = ModeleDocument.objects.filter(categorie="inscription", defaut=True).first()
                IDmodele = modele_defaut.pk if modele_defaut else None
                # Si aucun modèle n'existe, on en crée un et on l'affecte
                if IDmodele is None:
                    logger.warning(
                        "Aucun modèle de document par défaut pour 'inscription' trouvé. Création en cours...")

                    modele_defaut = ModeleDocument.objects.create(
                        categorie="inscription",
                        defaut=True,
                        nom="Modèle Inscriptions",
                        largeur="210",
                        hauteur="290",
                        objets=[]
                    )

                    IDmodele = modele_defaut.pk

            impression = utils_impression_inscription.Impression(dict_options=dict_options, IDmodele=IDmodele,
                                                                 generation_auto=False)
            for IDinscription, dictInscription in dict_inscriptions.items():
                logger.debug("Création du PDF de l'inscription ID%d..." % IDinscription)
                impression.Generation_document(dict_donnees={IDinscription: dictInscription})
                noms_fichiers[IDinscription] = {"nom_fichier": impression.Get_nom_fichier(),
                                                "valeurs": impression.Get_champs_fusion_pour_email("inscription",
                                                                                                   IDinscription)}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_inscription.Impression(dict_donnees=dict_inscriptions,
                                                                 dict_options=dict_options,
                                                                 IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()

        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}
