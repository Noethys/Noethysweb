# -*- coding: utf-8 -*-
#  Copyright (c) 2025 GIP RECIA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

# Fichier créé par Faouzia TEKAYA (GIP RECIA, branche emails-par-lot) — copié dans fiche_individu/utils/ car absent de upstream Ivan.
# Contient la classe Activites qui gère la récupération des données d'impression et l'impression des activités, notamment pour l'éditeur d'emails groupés des activités (inscriptions_activites_email).


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

        # champs famille/individu enrichis (adresse, téléphone, email...) — désactivé pour l'instant.
        # à activer si on veut exposer plus de champs dans les modèles de documents et emails d'activité.
        # pour activer : décommenter les 3 blocs ci-dessous et ajouter GetNomsChampsPossibles(mode="individu+famille")
        # dans la classe Activite de core/utils/utils_modeles_documents.py
        # liste_idfamille = list(Inscription.objects.filter(activite_id__in=liste_activites, famille__isnull=False).values_list("famille_id", flat=True).distinct())
        # infosIndividus = utils_infos_individus.Informations(liste_familles=liste_idfamille)
   
        dictDonnees = {}     
        dictChampsFusion = {}
        for activite in activites:
            activite_id = activite.pk

            # Données par activité - utilisées pour le PDF global (mode_email=False)
            dictDonnees[activite_id] = {
                "{ACTIVITE_NOM_LONG}": activite.nom,
                "{ACTIVITE_NOM_COURT}": activite.abrege or "",
            }

            # Données par inscription - utilisées pour les emails (mode_email=True)
            inscriptions = (
                Inscription.objects
                .filter(activite_id=activite_id, famille__isnull=False)
                .select_related("famille", "individu", "groupe", "categorie_tarif")
            )
            for inscription in inscriptions:
                dictChampsFusion[inscription.idinscription] = {
                    "{ACTIVITE_NOM_LONG}": activite.nom,
                    "{ACTIVITE_NOM_COURT}": activite.abrege or "",
                    "{IDINSCRIPTION}": str(inscription.idinscription),
                    "{DATE_DEBUT}": utils_dates.ConvertDateToFR(inscription.date_debut) if inscription.date_debut else "",
                    "{DATE_FIN}": utils_dates.ConvertDateToFR(inscription.date_fin) if inscription.date_fin else "",
                    "{GROUPE_NOM_LONG}": inscription.groupe.nom if inscription.groupe else "",
                    "{GROUPE_NOM_COURT}": inscription.groupe.abrege if inscription.groupe else "",
                    "{NOM_CATEGORIE_TARIF}": inscription.categorie_tarif.nom if inscription.categorie_tarif else "",
                    "{INDIVIDU_NOM}": inscription.individu.nom if inscription.individu else "",
                    "{INDIVIDU_PRENOM}": inscription.individu.prenom if inscription.individu else "",
                    "{INDIVIDU_DATE_NAISS}": utils_dates.ConvertDateToFR(inscription.individu.date_naiss) if inscription.individu and inscription.individu.date_naiss else "",
                    "{NOMBRE_INSCRIPTIONS}": str(dict_nb_inscriptions.get(activite_id, 0))
                }

                #à activer si on veut enrichir les champs famille/individu
                # Ajout des infos famille et individu (adresse, téléphone, email...)
                #dictChampsFusion[inscription.idinscription].update(
                #    infosIndividus.GetDictValeurs(mode="famille", ID=inscription.famille_id, formatChamp=True)
                #)

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
            for IDinscription, dictInscription in dictChampsFusion.items():
                logger.debug("Création du PDF de l'inscription ID%d..." % IDinscription)
                impression.Generation_document(dict_donnees={IDinscription: dictInscription})
                noms_fichiers[IDinscription] = {"nom_fichier": impression.Get_nom_fichier(),
                                                "valeurs": dictInscription}

        # Fabrication du PDF global
        nom_fichier = None
        if not mode_email:
            impression = utils_impression_activites.Impression(dict_donnees=dict_activites, dict_options=dict_options,
                                                                 IDmodele=dict_options["modele"].pk)
            nom_fichier = impression.Get_nom_fichier()
        logger.debug("Création des PDF terminée.")
        return {"champs": dictChampsFusion, "nom_fichier": nom_fichier, "noms_fichiers": noms_fichiers}
