# -*- coding: utf-8 -*-
#  Copyright (c) 2025 GIP RECIA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging

logger = logging.getLogger(__name__)
import datetime
from core.utils import utils_infos_individus, utils_texte, utils_conversion, utils_dates, utils_questionnaires
from core.models import Activite, Inscription, Famille
from django.db.models import Count
from fiche_individu.utils import utils_impression_activites


class Activites():
    def __init__(self):
        """ Récupération de toutes les données de base """
        logger.debug("Recherche toutes les activités...")
        self.questionnaires = utils_questionnaires.ChampsEtReponses(categorie="activite")

    def GetDonneesImpression(self, liste_activites=[]):
        """ Récupération des données d'impression des activités """
        logger.debug("Recherche des données d'impression pour les activités...")
        # Recherche les activités sélectionnées
        activites = Activite.objects.filter(pk__in=liste_activites)

        # Récupération du nombre d'inscriptions par activité
        activites_data = (
            Inscription.objects
            .filter(activite_id__in=liste_activites)
            .values("activite_id")
            .annotate(nombre_inscriptions=Count("activite_id"))
        )

        # Dictionnaire pour stocker le nombre d'inscriptions par activité
        dict_nb_inscriptions = {data["activite_id"]: data["nombre_inscriptions"] for data in activites_data}

        dictDonnees = {}
        dictChampsFusion = {}

        for activite in activites:
            activite_id = activite.pk
            nombre_inscriptions = dict_nb_inscriptions.get(activite_id, 0)

            # Récupérer les familles inscrites à cette activité
            familles = (
                Inscription.objects
                .filter(activite_id=activite_id, famille__isnull=False)
                .select_related("famille", "activite")
                .values(
                    "activite_id",
                    "activite__nom",
                    "famille_id",
                    "famille__nom",
                    "famille__mail"
                )
                .distinct()
            )

            # Mémorisation des données
            dictDonnee = {
                "{IDACTIVITE}": str(activite.pk),
                "{ACTIVITE_NOM_LONG}": activite.nom,
                "{ACTIVITE_NOM_COURT}": activite.abrege,
                "{NOMBRE_INSCRIPTIONS}": nombre_inscriptions,
                "{FAMILLES}": ", ".join(
                    [f"{famille['famille__nom']} ({famille['famille__mail']})" for famille in familles])
            }

            # Correction : récupérer les inscriptions liées à l'activité
            for inscription in Inscription.objects.filter(activite=activite):
                if inscription.famille:
                    for dictReponse in self.questionnaires.GetDonnees(inscription.famille_id):
                        dictDonnee[dictReponse["champ"]] = dictReponse["reponse"]

            dictDonnees[activite.pk] = dictDonnee
            # Champs de fusion pour Email
            dictChampsFusion[activite.pk] = {}
            for key, valeur in dictDonnee.items():
                if key.startswith("{"):
                    dictChampsFusion[activite.pk][key] = valeur

        return dictDonnees, dictChampsFusion

    def Impression(self, liste_activites=[], dict_options=None, mode_email=False):
        """ Impression des activités """
        # Récupération des données à partir des ID d'activités
        logger.debug("Recherche des données d'impression...")
        resultat = self.GetDonneesImpression(liste_activites)

        if resultat == False:
            return False
        dict_activites, dictChampsFusion = resultat

        # Envoi par email
        noms_fichiers = {}
        if mode_email:
            logger.debug("Création des PDF des activités à l'unité...")

            if dict_options and "modele" in dict_options and dict_options["modele"]:
                IDmodele = dict_options["modele"].pk
            else:
                from core.models import ModeleDocument
                modele_defaut = ModeleDocument.objects.filter(categorie="activite", defaut=True).first()
                IDmodele = modele_defaut.pk if modele_defaut else None

                # Si aucun modèle n'existe, on en crée un et on l'affecte
                if IDmodele is None:
                    logger.warning("Aucun modèle de document par défaut pour 'activite' trouvé. Création en cours...")

                    modele_defaut = ModeleDocument.objects.create(
                        categorie="activite",
                        defaut=True,
                        nom="Modèle Activités",
                        largeur="210",
                        hauteur="290",
                        objets=[]
                    )

                    IDmodele = modele_defaut.pk

            impression = utils_impression_activites.Impression(dict_options=dict_options, IDmodele=IDmodele,generation_auto=False)
            for IDactivite, dictActivite in dict_activites.items():
                logger.debug("Création du PDF de l'activité ID%d..." % IDactivite)
                impression.Generation_document(dict_donnees={IDactivite: dictActivite})
                noms_fichiers[IDactivite] = {"nom_fichier": impression.Get_nom_fichier(),
                                             "valeurs": impression.Get_champs_fusion_pour_email("activite", IDactivite)}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_activites.Impression(dict_donnees=dict_activites, dict_options=dict_options,
                                                                 IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()
        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}
