# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy

CATEGORIES = [
    ("saisie_libre", "Saisie libre"),
    ("releve_prestations", "Relevé des prestations"),
    ("reglement", "Règlement"),
    ("recu_reglement", "Reçu de règlement"),
    ("recu_don_oeuvres", "Reçu de don aux oeuvres"),
    ("facture", "Facture"),
    ("rappel", "Rappel"),
    ("attestation_presence", "Attestation de présence"),
    ("attestation_fiscale", "Attestation fiscale"),
    ("reservations", "Liste des réservations"),
    ("cotisation", "Cotisation"),
    ("mandat_sepa", "Mandat SEPA"),
    ("rappel_pieces_manquantes", "Rappel pièces manquantes"),
    ("portail", "Rappel des données du compte internet"),
    ("portail_demande_inscription", "Portail - Demande d'une inscription"),
    ("portail_demande_reservation", "Portail - Demande d'une réservation"),
    ("portail_demande_renseignement", "Portail - Demande de modification d'un renseignement"),
    ("portail_demande_facture", "Portail - Demande d'une facture"),
    ("portail_demande_recu_reglement", "Portail - Demande d'un reçu de règlement"),
    ("portail_demande_location", "Portail - Demande d'une location"),
    ("portail_places_disponibles", "Portail - Attribution de places disponibles"),
    ("portail_confirmation_reservations", "Portail - Confirmation des réservations"),
    ("portail_notification_message", "Portail - Notification d'un message"),
    ("location", "Location"),
    ("location_demande", "Demande de location"),
    ("commande_repas", "Commande de repas"),
    ("inscription", "Inscription"),
    ("devis", "Devis"),
]

MOTSCLES_STANDARDS = [
    ("{UTILISATEUR_NOM_COMPLET}", "Nom complet de l'utilisateur"),
    ("{UTILISATEUR_NOM}", "Nom de famille de l'utilisateur"),
    ("{UTILISATEUR_PRENOM}", "Prénom de l'utilisateur"),
    ("{UTILISATEUR_SIGNATURE}", "Signature de l'utilisateur"),
    ("{DATE_COURTE}", "Date du jour courte"),
    ("{DATE_LONGUE}", "Date du jour longue"),
    ("{ORGANISATEUR_NOM}", "Nom de l'organisateur"),
    ("{ORGANISATEUR_RUE}", "Rue de l'organisateur"),
    ("{ORGANISATEUR_CP}", "CP de l'organisateur"),
    ("{ORGANISATEUR_VILLE}", "Ville de l'organisateur"),
    ("{ORGANISATEUR_TEL}", "Téléphone de l'organisateur"),
    ("{ORGANISATEUR_MAIL}", "Email de l'organisateur"),
    ("{ORGANISATEUR_SITE}", "Site internet de l'organisateur"),
    ("{URL_PORTAIL}", "URL du portail famille"),
]

MOTSCLES = {

    "saisie_libre": [],

    "releve_prestations": [
        ("{DATE_EDITION_RELEVE}", "Date de l'édition du relevé"),
        ("{RESTE_DU}", "Reste dû indiqué par le relevé"),
    ],

    "reglement": [
        ("{ID_REGLEMENT}", "ID du règlement"),
        ("{DATE_REGLEMENT}", "Date du règlement"),
        ("{MODE_REGLEMENT}", "Mode de règlement"),
        ("{NOM_EMETTEUR}", "Nom de l'émetteur"),
        ("{NUM_PIECE}", "Numéro de la pièce"),
        ("{MONTANT_REGLEMENT}", "Montant du règlement"),
        ("{NOM_PAYEUR}", "Nom du payeur"),
        ("{NUM_QUITTANCIER}", "Numéro de quittancier"),
        ("{DATE_SAISIE}", "Date de saisie du règlement"),
        ("{DATE_DIFFERE}", "Date d'encaissement différé"),
    ],

    "recu_reglement": [
        ("{DATE_EDITION_RECU}", "Date d'édition du reçu"),
        ("{NUMERO_RECU}", "Numéro du reçu"),
        ("{ID_REGLEMENT}", "ID du règlement"),
        ("{DATE_REGLEMENT}", "Date du règlement"),
        ("{MODE_REGLEMENT}", "Mode de règlement"),
        ("{NOM_EMETTEUR}", "Nom de l'émetteur"),
        ("{NUM_PIECE}", "Numéro de la pièce"),
        ("{MONTANT_REGLEMENT}", "Montant du règlement"),
        ("{NOM_PAYEUR}", "Nom du payeur"),
        ("{NUM_QUITTANCIER}", "Numéro de quittancier"),
        ("{DATE_SAISIE}", "Date de saisie du règlement"),
        ("{DATE_DIFFERE}", "Date d'encaissement différé"),
    ],

    "recu_don_oeuvres": [
        ("{DATE_EDITION}", "Date d'édition du reçu"),
        ("{NUMERO_RECU}", "Numéro du reçu"),
        ("{NOM_DONATEUR}", "Nom du donateur"),
        ("{ADRESSE_DONATEUR}", "Adresse du donateur"),
        ("{DATE_REGLEMENT}", "Date du règlement"),
        ("{MODE_REGLEMENT}", "Mode du règlement"),
        ("{MONTANT_CHIFFRES}", "Montant en chiffres"),
        ("{MONTANT_LETTRES}", "Montant en lettres"),
    ],

    "facture": [
        ("{DATE_EDITION_FACTURE}", "Date d'édition de la facture"),
        ("{NUMERO_FACTURE}", "Numéro de facture"),
        ("{DATE_DEBUT}", "Date de début de la période de facturation"),
        ("{DATE_FIN}", "Date de fin de la période de facturation"),
        ("{DATE_ECHEANCE}", "Date d'échance du règlement"),
        ("{SOLDE}", "Solde de la facture"),
        ("{SOLDE_AVEC_REPORTS}", "Solde de la facture (reports inclus)"),
        ("{SOLDE_COMPTE}", "Solde du compte famille"),
    ],

    "rappel": [
        ("{DATE_EDITION_RAPPEL}", "Date d'édition de la lettre de rappel"),
        ("{NUMERO_RAPPEL}", "Numéro de le lattre de rappel"),
        ("{DATE_MIN}", "Date de début des impayés"),
        ("{DATE_MAX}", "Date de fin des impayés"),
        ("{DATE_REFERENCE}", "Date de référence"),
        ("{SOLDE_CHIFFRES}", "Solde du rappel en chiffres"),
        ("{SOLDE_LETTRES}", "Solde du rappel en lettres"),
    ],

    "attestation_presence": [
        ("{DATE_EDITION_ATTESTATION}", "Date d'édition de l'attestation"),
        ("{NUMERO_ATTESTATION}", "Numéro de l'attestation"),
        ("{DATE_DEBUT}", "Date de début de la période"),
        ("{DATE_FIN}", "Date de fin de la période"),
        ("{INDIVIDUS_CONCERNES}", "Liste des individus concernés"),
        ("{SOLDE}", "Solde de l'attestation"),
    ],

    "reservations": [
        ("{SOLDE}", "Solde du document"),
    ],

    "mandat_sepa": [
        ("{REFERENCE_UNIQUE_MANDAT}", "RUM (Référence Unique du Mandat)"),
        ("{DATE_SIGNATURE}", "Date de signature du mandat"),
    ],

    "cotisation": [
        ("{NUMERO_CARTE}", "Numéro de la carte"),
        ("{DATE_DEBUT}", "Date de début de validité de l'adhésion"),
        ("{DATE_FIN}", "Date de fin de validité de l'adhésion"),
        ("{NOM_TYPE_COTISATION}", "Nom du type d'adhésion"),
        ("{NOM_UNITE_COTISATION}", "Nom de l'unité d'adhésion"),
        ("{NOM_COTISATION}", "Nom de la cotisation (type + unité)"),
        ("{DATE_CREATION_CARTE}", "Date de création de la carte"),
        ("{MONTANT_FACTURE}", "Montant facturé"),
        ("{MONTANT_REGLE}", "Montant réglé"),
        ("{SOLDE_ACTUEL}", "Solde actuel"),
        ("{ACTIVITES}", "Activités associées"),
        ("{NOTES}", "Notes"),
    ],

    "attestation_fiscale": [
        ("{DATE_EDITION_COURT}", "Date d'édition court"),
        ("{DATE_EDITION_LONG}", "Date d'édition long"),
        ("{DATE_DEBUT}", "Date de début de la période"),
        ("{DATE_FIN}", "Date de fin de la période"),
        ("{MONTANT_FACTURE}", "Montant total facturé"),
        ("{MONTANT_REGLE}", "Montant réglé"),
        ("{MONTANT_IMPAYE}", "Montant impayé"),
        ("{MONTANT_FACTURE_LETTRES}", "Montant total facturé en lettres"),
        ("{MONTANT_REGLE_LETTRES}", "Montant réglé en lettres"),
        ("{MONTANT_IMPAYE_LETTRES}", "Montant impayé en lettres"),
    ],

    "rappel_pieces_manquantes": [
        ("{NOM_FAMILLE}", "Nom de la famille"),
        ("{LISTE_PIECES_MANQUANTES}", "Liste des pièces manquantes"),
    ],

    "portail": [
        ("{NOM_FAMILLE}", "Nom de la famille"),
        ("{IDENTIFIANT_INTERNET}", "Identifiant du compte internet"),
        ("{MOTDEPASSE_INTERNET}", "Mot de passe du compte internet"),
        ("{DATE_EXPIRATION_MOTDEPASSE}", "Date d'expiration du mot de passe du compte internet"),
    ],

    "portail_demande_inscription": [
        ("{DEMANDE_HORODATAGE}", "Date et heure de la demande"),
        ("{DEMANDE_DESCRIPTION}", "Description de la demande"),
        ("{DEMANDE_COMMENTAIRE}", "Commentaire de la demande"),
        ("{DEMANDE_TRAITEMENT_DATE}", "Date de traitement"),
        ("{DEMANDE_REPONSE}", "Réponse à la demande"),
    ],

    "portail_demande_renseignement": [
        ("{DEMANDE_HORODATAGE}", "Date et heure de la demande"),
        ("{DEMANDE_DESCRIPTION}", "Description de la demande"),
        ("{DEMANDE_COMMENTAIRE}", "Commentaire de la demande"),
        ("{DEMANDE_TRAITEMENT_DATE}", "Date de traitement"),
        ("{DEMANDE_REPONSE}", "Réponse à la demande"),
    ],

    "portail_demande_location": [
        ("{DEMANDE_HORODATAGE}", "Date et heure de la demande"),
        ("{DEMANDE_DESCRIPTION}", "Description de la demande"),
        ("{DEMANDE_COMMENTAIRE}", "Commentaire de la demande"),
        ("{DEMANDE_TRAITEMENT_DATE}", "Date de traitement"),
        ("{DEMANDE_REPONSE}", "Réponse à la demande"),
    ],

    "portail_demande_reservation": [
        ("{DEMANDE_HORODATAGE}", "Date et heure de la demande"),
        # ("{DEMANDE_DESCRIPTION}", "Description de la demande"),
        # ("{DEMANDE_COMMENTAIRE}", "Commentaire de la demande"),
        # ("{DEMANDE_TRAITEMENT_DATE}", "Date de traitement"),
        ("{DEMANDE_REPONSE}", "Réponse à la demande"),
        # ("{PERIODE_NOM}", "Nom de la période"),
        # ("{PERIODE_DATE_DEBUT}", "Date de début de la période"),
        # ("{PERIODE_DATE_FIN}", "Date de fin de la période"),
        ("{INDIVIDU_NOM}", "Nom de famille de l'individu concerné"),
        ("{INDIVIDU_PRENOM}", "Prénom de l'individu concerné"),
        ("{INDIVIDU_NOM_COMPLET}", "Nom et prénom de l'individu concerné"),
        # ("{TOTAL}", "Total des prestations de la période"),
        # ("{REGLE}", "Total déjà réglé pour la période"),
        # ("{SOLDE}", "Solde de la période"),
    ],

    "portail_places_disponibles": [
        ("{DETAIL_PLACES}", "Détail des places disponibles"),
        ("{INDIVIDU_NOM_COMPLET}", "Nom complet de l'individu"),
        ("{INDIVIDU_NOM}", "Nom de famille de l'individu"),
        ("{INDIVIDU_PRENOM}", "Prénom de l'individu"),
    ],

    "portail_confirmation_reservations": [
        ("{DETAIL_MODIFICATIONS}", "Détail des modifications de réservations"),
        ("{ACTIVITE_NOM}", "Nom de l'activité"),
        ("{PERIODE_NOM}", "Nom de la période"),
        ("{INDIVIDU_NOM_COMPLET}", "Nom complet de l'individu"),
        ("{INDIVIDU_NOM}", "Nom de famille de l'individu"),
        ("{INDIVIDU_PRENOM}", "Prénom de l'individu"),
    ],

    "portail_notification_message": [
        ("{URL_MESSAGE}", "URL du message"),
    ],

    "portail_demande_facture": [
        ("{DEMANDE_HORODATAGE}", "Date et heure de la demande"),
        ("{DEMANDE_DESCRIPTION}", "Description de la demande"),
        ("{DEMANDE_COMMENTAIRE}", "Commentaire de la demande"),
        ("{DEMANDE_TRAITEMENT_DATE}", "Date de traitement"),
        ("{DEMANDE_REPONSE}", "Réponse à la demande"),
    ],

    "portail_demande_recu_reglement": [
        ("{DEMANDE_HORODATAGE}", "Date et heure de la demande"),
        ("{DEMANDE_DESCRIPTION}", "Description de la demande"),
        ("{DEMANDE_COMMENTAIRE}", "Commentaire de la demande"),
        ("{DEMANDE_TRAITEMENT_DATE}", "Date de traitement"),
        ("{DEMANDE_REPONSE}", "Réponse à la demande"),
    ],

    "location": [
        ("{IDLOCATION}", "ID de la location"),
        ("{IDPRODUIT}", "ID du produit"),
        ("{DATE_DEBUT}", "Date de début"),
        ("{DATE_FIN}", "Date de fin"),
        ("{HEURE_DEBUT}", "Heure de début"),
        ("{HEURE_FIN}", "Heure de fin"),
        ("{NOM_PRODUIT}", "Nom du produit"),
        ("{NOM_CATEGORIE}", "Nom de la catégorie"),
        ("{NOTES}", "Observations"),
    ],

    "location_demande": [
        ("{IDDEMANDE}", "ID de la demande"),
        ("{DATE}", "Date de la demande"),
        ("{HEURE}", "Heure de la demande"),
        ("{CATEGORIES}", "Catégories demandées"),
        ("{PRODUITS}", "Produits demandés"),
        ("{NOTES}", "Observations"),
    ],

    "commande_repas": [
        ("{NOM_COMMANDE}", "Nom de la commande"),
        ("{DATE_DEBUT}", "Date de début de la période"),
        ("{DATE_FIN}", "Date de fin de la période"),
    ],

    "inscription": [
        ("{IDINSCRIPTION}", "ID de l'inscription"),
        ("{DATE_DEBUT}", "Date de début de l'inscription"),
        ("{DATE_FIN}", "Date de fin de l'inscription"),
        ("{ACTIVITE_NOM_LONG}", "Nom de l'activité long"),
        ("{ACTIVITE_NOM_COURT}", "Nom de l'activité abrégé"),
        ("{GROUPE_NOM_LONG}", "Nom du groupe long"),
        ("{GROUPE_NOM_COURT}", "Nom du groupe abrégé"),
        ("{NOM_CATEGORIE_TARIF}", "Nom de la catégorie de tarif"),
        ("{INDIVIDU_NOM}", "Nom de famille de l'individu"),
        ("{INDIVIDU_PRENOM}", "Prénom de l'individu"),
        ("{INDIVIDU_DATE_NAISS}", "Date de naissance de l'individu"),
    ],

    "devis": [
        ("{DATE_EDITION_DEVIS}", "Date d'édition du devis"),
        ("{NUMERO_DEVIS}", "Numéro du devis"),
        ("{DATE_DEBUT}", "Date de début de la période"),
        ("{DATE_FIN}", "Date de fin de la période"),
        ("{INDIVIDUS_CONCERNES}", "Liste des individus concernés"),
        ("{SOLDE}", "Solde du devis"),
    ],

}


def Get_mots_cles(categorie=""):
    listeTemp = copy.deepcopy(MOTSCLES_STANDARDS)
    if categorie in MOTSCLES:
        listeTemp.extend(MOTSCLES[categorie])
    return listeTemp


