#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, decimal, uuid, os
from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.files.storage import get_storage_class
from django.templatetags.static import static
from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django_resized import ResizedImageField
from django_cryptography.fields import encrypt
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField
from core.data import data_civilites
from core.data.data_modeles_impressions import CATEGORIES as CATEGORIES_MODELES_IMPRESSIONS
from core.data.data_modeles_emails import CATEGORIES as CATEGORIES_MODELES_EMAILS
from core.data.data_modeles_sms import CATEGORIES as CATEGORIES_MODELES_SMS
from core.data.data_modeles_word import CATEGORIES as CATEGORIES_MODELES_WORD
from individus.utils.utils_transports import Get_liste_choix_categories
from core.utils import utils_permissions
from core.utils import utils_texte, utils_dates

CATEGORIES_TRANSPORTS = Get_liste_choix_categories()

JOURS_SEMAINE = [(0, "L"), (1, "M"), (2, "M"), (3, "J"), (4, "V"), (5, "S"), (6, "D")]
JOURS_COMPLETS_SEMAINE = [(0, "Lundi"), (1, "Mardi"), (2, "Mercredi"), (3, "Jeudi"), (4, "Vendredi"), (5, "Samedi"), (6, "Dimanche")]

LISTE_MOIS = [(1, "Janvier"), (2, "Février"), (3, "Mars"), (4, "Avril"),
              (5, "Mai"), (6, "Juin"), (7, "Juillet"), (8, "Août"),
              (9, "Septembre"), (10, "Octobre"), (11, "Novembre"), (12, "Décembre")
              ]

LISTE_VACANCES = [("Février", "Février"), ("Pâques", "Pâques"), ("Eté", "Eté"), ("Toussaint", "Toussaint"), ("Noël", "Noël")]

LISTE_TYPES_RENSEIGNEMENTS = [
    (1, u"Date de naissance"),
    (2, u"Lieu de naissance"),
    (3, u"Numéro de sécurité sociale"),
    (6, u"Médecin traitant"),
    (12, u"Quotient familial"),
    (7, u"Caisse d'allocations"),
    (8, u"Numéro d'allocataire"),
    (9, u"Titulaire allocataire"),
    (10, u"Titulaire Hélios"),
    (11, u"Code comptable"),
    ]


LISTE_METHODES_TARIFS = [
    { "code": "montant_unique", "label":u"Montant unique", "type": "unitaire", "nbre_lignes_max": 1, "entete": None, "champs": ("montant_unique", "montant_questionnaire"), "champs_obligatoires": ("montant_unique",), "tarifs_compatibles": ("JOURN", "FORFAIT", "CREDIT") },
    { "code": "qf", "label":u"En fonction du quotient familial", "type": "unitaire", "nbre_lignes_max": None, "entete": "tranche", "champs": ("qf_min", "qf_max", "montant_unique"), "champs_obligatoires": ("qf_min", "qf_max", "montant_unique"), "tarifs_compatibles": ("JOURN", "FORFAIT", "CREDIT") },

    { "code": "horaire_montant_unique", "label":u"Montant unique en fonction d'une tranche horaire", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "temps_facture", "montant_unique", "montant_questionnaire", "label"), "champs_obligatoires": ("heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "montant_unique"), "tarifs_compatibles": ("JOURN",) },
    { "code": "horaire_qf", "label":u"En fonction d'une tranche horaire et du quotient familial", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("qf_min", "qf_max", "heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "temps_facture", "montant_unique", "label"), "champs_obligatoires": ("qf_min", "qf_max", "heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "montant_unique"), "tarifs_compatibles": ("JOURN",) },

    { "code": "duree_montant_unique", "label":u"Montant unique en fonction d'une durée", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("duree_min", "duree_max", "temps_facture", "montant_unique", "montant_questionnaire", "label"), "champs_obligatoires": ("duree_min", "duree_max", "montant_unique"), "tarifs_compatibles": ("JOURN",) },
    { "code": "duree_qf", "label":u"En fonction d'une durée et du quotient familial", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("qf_min", "qf_max", "duree_min", "duree_max", "temps_facture", "montant_unique", "label"), "champs_obligatoires": ("qf_min", "qf_max", "duree_min", "duree_max", "montant_unique"), "tarifs_compatibles": ("JOURN",) },

    { "code": "montant_unique_date", "label":u"Montant unique en fonction de la date", "type": "unitaire", "nbre_lignes_max": None, "entete": None, "champs": ("date", "montant_unique", "label"), "champs_obligatoires": ("date", "montant_unique"), "tarifs_compatibles": ("JOURN",) },
    { "code": "qf_date", "label":u"En fonction de la date et du quotient familial", "type": "unitaire", "nbre_lignes_max": None, "entete": None, "champs": ("date", "qf_min", "qf_max", "montant_unique", "label"), "champs_obligatoires": ("date", "qf_min", "qf_max", "montant_unique"), "tarifs_compatibles": ("JOURN",) },

    # { "code": "variable", "label":u"Tarif libre (Saisi par l'utilisateur)"), "type": "unitaire", "nbre_lignes_max": 0, "entete": None, "champs": (), "champs_obligatoires": (), "tarifs_compatibles": ("JOURN",) },
    # { "code": "choix", "label":u"Tarif au choix (Sélectionné par l'utilisateur)"), "type": "unitaire", "nbre_lignes_max": None, "entete": None, "champs": ("montant_unique", "label"), "champs_obligatoires": ("montant_unique",), "tarifs_compatibles": ("JOURN", "FORFAIT",) },

    { "code": "montant_evenement", "label":u"Montant de l'évènement", "type": "unitaire", "nbre_lignes_max": 0, "entete": None, "champs": (), "champs_obligatoires": (), "tarifs_compatibles": ("JOURN",) },

    { "code": "montant_unique_nbre_ind", "label":u"Montant unique en fonction du nombre d'individus de la famille présents", "type": "unitaire", "nbre_lignes_max": 1, "entete": "tranche", "champs": ("montant_enfant_1", "montant_enfant_2", "montant_enfant_3", "montant_enfant_4", "montant_enfant_5", "montant_enfant_6", ), "champs_obligatoires": ("montant_enfant_1",), "tarifs_compatibles": ("JOURN",) },
    { "code": "qf_nbre_ind", "label":u"En fonction du quotient familial et du nombre d'individus de la famille présents", "type": "unitaire", "nbre_lignes_max": None, "entete": "tranche", "champs": ("qf_min", "qf_max", "montant_enfant_1", "montant_enfant_2", "montant_enfant_3", "montant_enfant_4", "montant_enfant_5", "montant_enfant_6",), "champs_obligatoires": ("qf_min", "qf_max", "montant_enfant_1"), "tarifs_compatibles": ("JOURN",) },
    { "code": "horaire_montant_unique_nbre_ind", "label":u"Montant unique en fonction du nombre d'individus de la famille présents et de la tranche horaire", "type": "unitaire", "nbre_lignes_max": None, "entete": "tranche", "champs": ("heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "temps_facture", "montant_enfant_1", "montant_enfant_2", "montant_enfant_3", "montant_enfant_4", "montant_enfant_5", "montant_enfant_6", "label"), "champs_obligatoires": ("heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "montant_enfant_1"), "tarifs_compatibles": ("JOURN",) },
    { "code": "montant_unique_nbre_ind_degr", "label":u"Montant dégressif en fonction du nombre d'individus de la famille présents", "type": "unitaire", "nbre_lignes_max": 1, "entete": "tranche", "champs": ("montant_enfant_1", "montant_enfant_2", "montant_enfant_3", "montant_enfant_4", "montant_enfant_5", "montant_enfant_6", ), "champs_obligatoires": ("montant_enfant_1",), "tarifs_compatibles": ("JOURN",) },
    { "code": "qf_nbre_ind_degr", "label":u"Montant dégressif en fonction du quotient familial et du nombre d'individus de la famille présents", "type": "unitaire", "nbre_lignes_max": None, "entete": "tranche", "champs": ("qf_min", "qf_max", "montant_enfant_1", "montant_enfant_2", "montant_enfant_3", "montant_enfant_4", "montant_enfant_5", "montant_enfant_6", ), "champs_obligatoires": ("qf_min", "qf_max", "montant_enfant_1"), "tarifs_compatibles": ("JOURN",) },
    { "code": "horaire_montant_unique_nbre_ind_degr", "label":u"Montant dégressif en fonction du nombre d'individus de la famille présents et de la tranche horaire", "type": "unitaire", "nbre_lignes_max": None, "entete": "tranche", "champs": ("heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "temps_facture", "montant_enfant_1", "montant_enfant_2", "montant_enfant_3", "montant_enfant_4", "montant_enfant_5", "montant_enfant_6", "label"), "champs_obligatoires": ("heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "montant_enfant_1"), "tarifs_compatibles": ("JOURN",) },

    { "code": "duree_coeff_montant_unique", "label":u"Montant au prorata d'une durée", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("duree_min", "duree_max", "duree_seuil", "duree_plafond", "duree_arrondi", "unite_horaire", "montant_unique", "montant_min", "montant_max", "montant_questionnaire", "ajustement", "label"), "champs_obligatoires": ("unite_horaire", "montant_unique"), "tarifs_compatibles": ("JOURN",) },
    { "code": "duree_coeff_qf", "label":u"Montant au prorata d'une durée et selon le quotient familial", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("qf_min", "qf_max", "duree_min", "duree_max", "duree_seuil", "duree_plafond", "duree_arrondi", "unite_horaire", "montant_unique", "montant_min", "montant_max", "ajustement", "label"), "champs_obligatoires": ("qf_min", "qf_max", "unite_horaire", "montant_unique"), "tarifs_compatibles": ("JOURN",) },

    { "code": "taux_montant_unique", "label":u"Par taux d'effort", "type": "unitaire", "nbre_lignes_max": 1, "entete": None, "champs": ("taux", "montant_min", "montant_max", "ajustement", "label"), "champs_obligatoires": ("taux",), "tarifs_compatibles": ("JOURN",) },
    { "code": "taux_qf", "label":u"Par taux d'effort et par tranches de QF", "type": "unitaire", "nbre_lignes_max": None, "entete": None, "champs": ("qf_min", "qf_max", "taux", "montant_min", "montant_max", "ajustement", "label"), "champs_obligatoires": ("qf_min", "qf_max", "taux",), "tarifs_compatibles": ("JOURN",) },
    { "code": "taux_date", "label":u"Par taux d'effort et par date", "type": "unitaire", "nbre_lignes_max": None, "entete": None, "champs": ("date", "taux", "montant_min", "montant_max", "ajustement", "label"), "champs_obligatoires": ("date", "taux"), "tarifs_compatibles": ("JOURN",)},
    { "code": "duree_taux_montant_unique", "label":u"Par taux d'effort et en fonction d'une durée", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("duree_min", "duree_max", "temps_facture", "taux", "montant_min", "montant_max", "ajustement", "label"), "champs_obligatoires": ("duree_min", "duree_max", "taux"), "tarifs_compatibles": ("JOURN",) },
    { "code": "duree_taux_qf", "label":u"Par taux d'effort et par tranches de QF en fonction d'une durée", "type": "horaire", "nbre_lignes_max": None, "entete": None, "champs": ("qf_min", "qf_max", "duree_min", "duree_max", "temps_facture", "taux", "montant_min", "montant_max", "ajustement", "label"), "champs_obligatoires": ("qf_min", "qf_max", "duree_min", "duree_max", "taux"), "tarifs_compatibles": ("JOURN",) },

    # Lignes PSU
    # { "code": "forfait_contrat", "label":u"Forfait contrat"), "type": "unitaire", "nbre_lignes_max": 0, "entete": None, "champs": (), "champs_obligatoires": (), "tarifs_compatibles": ("CREDIT",) },
    # { "code": "psu_revenu", "label":u"Barême PSU selon revenus"), "type": "unitaire", "nbre_lignes_max": None, "entete": None, "champs": ("revenu_min", "revenu_max", "taux", "montant_min", "montant_max", "ajustement"), "champs_obligatoires": ("revenu_min", "revenu_max", "taux"), "tarifs_compatibles": ("BAREME",) },
    # { "code": "psu_qf", "label":u"Barême PSU selon QF"), "type": "unitaire", "nbre_lignes_max": None, "entete": None, "champs": ("qf_min", "qf_max", "taux", "montant_min", "montant_max", "ajustement"), "champs_obligatoires": ("qf_min", "qf_max", "taux"), "tarifs_compatibles": ("BAREME",) },

    # Lignes PRODUITS
    # {"code": "produit_montant_unique", "label":u"Montant unique", "type": "unitaire", "nbre_lignes_max": 1, "entete": None, "champs": ("montant_unique",), "champs_obligatoires": ("montant_unique",), "tarifs_compatibles": ("PRODUIT",)},
    # {"code": "produit_proportionnel_quantite", "label":u"Montant proportionnel à la quantité", "type": "unitaire", "nbre_lignes_max": 1, "entete": None, "champs": ("montant_unique",), "champs_obligatoires": ("montant_unique",), "tarifs_compatibles": ("PRODUIT",)},

]

DICT_COLONNES_TARIFS = {
    "tranche": {"label": "Tranche", "largeur": 60, "editeur": None, "infobulle": "Tranche"},
    "qf_min": {"label": "QF min >=", "largeur": 70, "editeur": "decimal", "infobulle": "Quotient familial minimal"},
    "qf_max": {"label": "QF max <=", "largeur": 70, "editeur": "decimal", "infobulle": "Quotient familial maximal"},
    "revenu_min": {"label": "Revenu min >=", "largeur": 70, "editeur": "decimal", "infobulle": "Revenu minimal"},
    "revenu_max": {"label": "Revenu max <=", "largeur": 70, "editeur": "decimal", "infobulle": "Revenu maximal"},
    "montant_unique": {"label": "Tarif", "largeur": 70, "editeur": "decimal4", "infobulle": "Montant"},
    "montant_questionnaire": {"label": "Tarif questionnaire", "largeur": 130, "editeur": "questionnaire", "infobulle": "Montant renseigné dans les questionnaires familiaux ou individuels"},
    "montant_enfant_1": {"label": "Tarif 1 ind.", "largeur": 60, "editeur": "decimal4", "infobulle": "Montant"},
    "montant_enfant_2": {"label": "Tarif 2 ind.", "largeur": 60, "editeur": "decimal4", "infobulle": "Montant"},
    "montant_enfant_3": {"label": "Tarif 3 ind.", "largeur": 60, "editeur": "decimal4", "infobulle": "Montant"},
    "montant_enfant_4": {"label": "Tarif 4 ind.", "largeur": 60, "editeur": "decimal4", "infobulle": "Montant"},
    "montant_enfant_5": {"label": "Tarif 5 ind.", "largeur": 60, "editeur": "decimal4", "infobulle": "Montant"},
    "montant_enfant_6": {"label": "Tarif 6 ind.", "largeur": 60, "editeur": "decimal4", "infobulle": "Montant"},
    "nbre_enfants": {"label": "Nb enfants", "largeur": 70, "editeur": None, "infobulle": "Nombre d'enfants"},
    "coefficient": {"label": "Coefficient", "largeur": 70, "editeur": "decimal", "infobulle": "Coefficient"},
    "montant_min": {"label": "Montant min", "largeur": 70, "editeur": "decimal4", "infobulle": "Montant minimal"},
    "montant_max": {"label": "Montant max", "largeur": 70, "editeur": "decimal4", "infobulle": "Montant maximal"},
    "heure_debut_min": {"label": "Heure Début min >=", "largeur": 77, "editeur": "heure", "infobulle": "Heure de début minimale"},
    "heure_debut_max": {"label": "Heure Début max <=", "largeur": 77, "editeur": "heure", "infobulle": "Heure de début maximale"},
    "heure_fin_min": {"label": "Heure Fin min >=", "largeur": 75, "editeur": "heure", "infobulle": "Heure de fin minimale"},
    "heure_fin_max": {"label": "Heure Fin max <=", "largeur": 75, "editeur": "heure", "infobulle": "Heure de fin maximale"},
    "duree_min": {"label": "Durée min >=", "largeur": 70, "editeur": "heure", "infobulle": "Durée minimale"},
    "duree_max": {"label": "Durée max <=", "largeur": 70, "editeur": "heure", "infobulle": "Durée maximale"},
    "date": {"label": "Date", "largeur": 80, "editeur": "date", "infobulle": "Date"},
    "label": {"label": "Label de la prestation (Optionnel)", "largeur": 220, "editeur": None, "infobulle": "Label de la prestation. Variables disponibles :\n{QUANTITE}, {TEMPS_REALISE}, {TEMPS_FACTURE}, {HEURE_DEBUT}, {HEURE_FIN}."},
    "temps_facture": {"label": "Temps facturé (pour la CAF)", "largeur": 90, "editeur": "heure", "infobulle": "Temps facturé"},
    "unite_horaire": {"label": "Unité horaire", "largeur": 70, "editeur": "heure", "infobulle": "Unité horaire de base"},
    "duree_seuil": {"label": "Durée seuil", "largeur": 70, "editeur": "heure", "infobulle": "Durée seuil"},
    "duree_plafond": {"label": "Durée plafond", "largeur": 70, "editeur": "heure", "infobulle": "Durée plafond"},
    "duree_arrondi": {"label": "Durée arrondi", "largeur": 70, "editeur": "heure", "infobulle": "Durée arrondi"},
    "taux": {"label": "Taux", "largeur": 70, "editeur": "decimal6", "infobulle": "Taux d'effort"},
    "ajustement": {"label": "Majoration/Déduction", "largeur": 75, "editeur": "decimal4", "infobulle": "Montant à majorer ou à déduire sur le tarif"},
}

CATEGORIES_RATTACHEMENT = [(1, "Représentant"), (2, "Enfant"), (3, "Contact")]

LISTE_CATEGORIES_QUESTIONNAIRES = [
    ("individu", "Individu"),
    ("famille", "Famille"),
    ("categorie_produit", "Catégorie de produits"),
    ("produit", "Produit"),
    ("location", "Location"),
    ("location_demande", "Demande de location"),
    ("inscription", "Inscription"),
    ("collaborateur", "Collaborateur"),
    ("contrat_collaborateur", "Contrat collaborateur"),
    ]

LISTE_ETATS_CONSO = [
    ("reservation", "Réservation"),
    ("present", "Présent"),
    ("absenti", "Absence injustifiée"),
    ("absentj", "Absence justifiée"),
    ("attente", "Attente"),
    ("refus", "Refus"),
]

LISTE_CONTROLES_QUESTIONNAIRES = [
    {"code": "ligne_texte", "label":u"Ligne de texte", "image": "Texte_ligne.png", "filtre": "texte"},
    {"code": "bloc_texte", "label":u"Bloc de texte multiligne", "image": "Texte_bloc.png", "options": {"hauteur":60}, "filtre": "texte" },
    {"code": "entier", "label":u"Nombre entier", "image": "Ctrl_nombre.png", "options": {"min":0, "max":99999}, "filtre": "entier" },
    {"code": "decimal", "label":u"Nombre décimal", "image": "Ctrl_decimal.png", "options": {"min":0, "max":99999}, "filtre": "decimal" },
    {"code": "montant", "label":u"Montant", "image": "Euro.png", "filtre": "montant" },
    {"code": "liste_deroulante", "label":u"Liste déroulante", "image": "Ctrl_choice.png", "options":{"choix":None}, "filtre": "choix" },
    {"code": "liste_coches", "label":u"Sélection multiple", "image": "Coches.png", "options": {"hauteur":-1, "choix":None} , "filtre": "choix"},
    {"code": "case_coche", "label":u"Case à cocher", "image": "Ctrl_coche.png" , "filtre": "coche"},
    {"code": "date", "label":u"Date", "image": "Jour.png" , "filtre": "date"},
    {"code": "slider", "label":u"Réglette", "image": "Reglette.png", "options": {"hauteur":-1, "min":0, "max":100}, "filtre": "entier" },
    {"code": "couleur", "label":u"Couleur", "image": "Ctrl_couleur.png", "options": {"hauteur":20}, "filtre": None},
    # {"code": "documents", "label":u"Porte-documents", "image": "Document.png", "options": {"hauteur":60}, "filtre": None},
    {"code": "codebarres", "label":u"Code-barres", "image": "Codebarres.png", "options": {"norme":"39"}, "filtre": "texte" },
    # {"code": "rfid", "label":u"Badge RFID", "image": "Rfid.png" , "filtre": "texte"},
    ]


LISTE_CATEGORIES_TIERS = [
    (1, "Personne physique"),
    (20, "Etat ou établissement public national"),
    (21, "Région"),
    (22, "Département"),
    (23, "Commune"),
    (24, "Groupement de collectivités"),
    (25, "Caisse des écoles"),
    (26, "CCAS"),
    (27, "Etablissement public de santé"),
    (28, "Ecole nationale de la santé publique"),
    (29, "Autre établissement publique ou organisme international"),
    (50, "Personne morale de droit privé autre qu'organisme social"),
    (60, "Caisse de sécurité sociale régime général"),
    (61, "Caisse de sécurité sociale régime agricole"),
    (62, "Sécurité sociale des travailleurs non salariés et professions non agricoles"),
    (63, "Autre régime obligatoire de sécurité sociale"),
    (64, "Mutuelle ou organisme d'assurance"),
    (65, "Autre tiers payant"),
    (70, "CNRACL"),
    (71, "IRCANTEC"),
    (72, "ASSEDIC"),
    (73, "Caisse mutualiste de retraite complémentaire"),
    (74, "Autre organisme social"),
    ]

LISTE_NATURES_JURIDIQUES = [
    (0, "Inconnu"),
    (1, "Particulier"),
    (2, "Artisan / commerçant / agriculteur"),
    (3, "Société"),
    (4, "CAM ou Caisse appliquant les mêmes règles"),
    (5, "Caisse complémentaire"),
    (6, "Association"),
    (7, "Etat ou organisme d'état"),
    (8, "Etablissement public national"),
    (9, "Collectivité territoriale / EPL / EPS"),
    (10, "Etat étranger"),
    (11, "CAF"),
    ]

LISTE_TYPES_ID_TIERS = [
    (9999, "Aucun"),
    (1, "01 - SIRET"),
    (2, "02 - SIREN"),
    (3, "03 - FINESS"),
    (4, "04 - NIR"),
    ]

CHOIX_AUTORISATIONS = [(None, "Autorisation non précisée"), (1, "Responsable légal(e)"), (2, "Contacter en cas d'urgence"), (3, "Raccompagnement autorisé"), (4, "Raccompagnement interdit")]

CHOIX_CATEGORIE_MODELE_DOCUMENT = [("fond", "Calque de fond"), ("facture", "Facture"), ("rappel", "Lettre de rappel"),
                                   ("attestation", "Attestation de présence"), ("reglement", "Règlement"),
                                   ("individu", "Individu"), ("famille", "Famille"), ("inscription", "Inscription"),
                                   ("cotisation", "Adhésion"), ("attestation_fiscale", "Attestation fiscale"),
                                   ("devis", "Devis"), ("location", "Location"),
                                   ("location_demande", "Demande de location")]

CHOIX_FORMAT_EXPORT_TRESOR = [
    ("pes", "PES v2 ORMC Recette"),
    ("magnus", "Gestion financière/Magnus Berger-Levrault"),
    ("jvs", "Millesime Online JVS"),
]

CHOIX_FORMAT_PRELEVEMENTS = [
    ("prive", "Secteur privé"),
    ("public_dft", "Secteur public DFT"),
]



def get_uuid():
    return uuid.uuid4()

def get_uuid_path(instance, filename):
    """ Renvoie un nom de fichier uuid """
    base_chemin = instance._meta.db_table
    if hasattr(instance, "get_upload_path"):
        base_chemin = os.path.join(base_chemin, instance.get_upload_path())
    return os.path.join(base_chemin, "%s.%s" % (get_uuid(), filename.split('.')[-1]))

def get_storage(nom_champ=None):
    """ Renvoie la classe de stockage souhaitée """
    class_storage = getattr(settings, "STORAGE_%s" % nom_champ.upper(), "django.core.files.storage.FileSystemStorage")
    return get_storage_class(class_storage)


class AdresseMail(models.Model):
    idadresse = models.AutoField(verbose_name="ID", db_column='IDadresse', primary_key=True)
    adresse = encrypt(models.EmailField(verbose_name="Adresse d'envoi", max_length=300, help_text="Saisissez l'adresse mail utilisée."))
    motdepasse = encrypt(models.CharField(verbose_name="Mot de passe", max_length=300, blank=True, null=True, help_text="Saisissez le mot de passe de la messagerie."))
    hote = encrypt(models.CharField(verbose_name="Hôte", max_length=300, blank=True, null=True, help_text="Saisissez le nom de l'hôte de la messagerie (Ex: smtp.orange.fr, smtp.gmail.com...)."))
    port = models.IntegerField(verbose_name="Port", blank=True, null=True, help_text="Saisissez le numéro de port (Ex: 995, 465...)")
    use_ssl = models.BooleanField(verbose_name="SSL", default=False, help_text="Cochez cette case si la messagerie exige le protocole SSL.")
    use_tls = models.BooleanField(verbose_name="TLS", default=False, help_text="Cochez cette case si la messagerie exige le protocole TLS.")
    utilisateur = encrypt(models.CharField(verbose_name="Utilisateur", max_length=300, blank=True, null=True, help_text="Saisissez le nom d'utilisateur (Souvent identique à l'adresse mail)."))
    nom_adresse = models.CharField(verbose_name="Adresse affichée", max_length=300, blank=True, null=True, help_text="Saisissez le nom ou l'adresse que vous souhaitez voir apparaître dans le client de messagerie du destinataire.")
    moteur = models.CharField(verbose_name="Moteur", max_length=200, choices=[("smtp", "SMTP"), ("mailjet", "Mailjet"), ("console", "Console")], help_text="Sélectionnez un moteur d'expédition (Smtp ou Mailjet).")
    parametres = models.CharField(verbose_name="Paramètres", max_length=500, blank=True, null=True)
    actif = models.BooleanField(verbose_name="Actif", default=True, help_text="Décochez la case pour désactiver cette adresse.")
    lien_desinscription = models.BooleanField(verbose_name="Insérer un lien de désinscription dans les mails groupés", default=True, help_text="Un lien de désinscription sera inséré à la fin de chaque mail envoyé par lot.")

    class Meta:
        db_table = 'adresses_mail'
        verbose_name = "adresse Mail"
        verbose_name_plural = "adresses Mail"

    def __str__(self):
        if self.adresse:
            return "%s (%s)" % (self.adresse, self.get_moteur_display())
        return "Adresse mail"

    def Get_parametre(self, nom=""):
        try:
            dict_parametres = {param.split("==")[0]: param.split("==")[1] for param in self.parametres.split("##")}
            return dict_parametres[nom]
        except:
            return None


class ConfigurationSMS(models.Model):
    idconfiguration = models.AutoField(verbose_name="ID", db_column='IDconfiguration', primary_key=True)
    moteur = models.CharField(verbose_name="Moteur", max_length=200, choices=[("mailjet", "Mailjet"), ("ovh", "OVH"), ("brevo", "Brevo")], help_text="Sélectionnez un moteur d'expédition.")
    token = encrypt(models.CharField(verbose_name="Token", max_length=300, blank=True, null=True, help_text="Saisissez le token qui vous a été communiqué par votre fournisseur."))
    nom_exp = models.CharField(verbose_name="Nom de l'expéditeur", max_length=11, blank=True, null=True, help_text="Saisissez le nom d'expéditeur qui doit apparaître dans le SMS (11 caractères max).")
    nbre_caracteres = models.IntegerField(verbose_name="Nbre caractères max.", default=160, help_text="Précisez le nombre de caractères maximal accepté pour un SMS (160 par défaut).")
    montant_unitaire = models.DecimalField(verbose_name="Montant unitaire", max_digits=10, decimal_places=4, default=0.0, help_text="Indiquez le coût unitaire d'un SMS.")
    solde = models.IntegerField(verbose_name="Solde de SMS", blank=True, null=True, help_text="Précisez le nombre approximatif de SMS restants sur votre compte prépayé.")
    nom_compte = models.CharField(verbose_name="Nom du compte", max_length=200, blank=True, null=True, help_text="Saisissez le nom du compte.")
    identifiant = models.CharField(verbose_name="Identifiant", max_length=200, blank=True, null=True, help_text="Saisissez l'identifiant de l'utilisateur.")
    motdepasse = encrypt(models.CharField(verbose_name="Mot de passe", max_length=200, blank=True, null=True, help_text="Saisissez le mot de passe de l'utilisateur."))

    class Meta:
        db_table = 'configurations_sms'
        verbose_name = "configuration SMS"
        verbose_name_plural = "configurations SMS"

    def __str__(self):
        return self.nom_exp if self.nom_exp else "Configuration SMS"


class Structure(models.Model):
    idstructure = models.AutoField(verbose_name="ID", db_column="IDstructure", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    rue = models.CharField(verbose_name="Rue", max_length=200, blank=True)
    cp = models.CharField(verbose_name="Code postal", max_length=50, blank=True)
    ville = models.CharField(verbose_name="Ville", max_length=200, blank=True)
    tel = models.CharField(verbose_name="Téléphone", max_length=200, blank=True)
    fax = models.CharField(verbose_name="Fax", max_length=200, blank=True)
    mail = models.EmailField(verbose_name="Email", max_length=300, blank=True)
    site = models.CharField(verbose_name="Site internet", max_length=200, blank=True)
    logo = ResizedImageField(verbose_name="Logo", upload_to=get_uuid_path, blank=True, null=True)
    gps = models.CharField(verbose_name="GPS", max_length=200, blank=True, null=True)
    logo_update = models.DateTimeField(verbose_name="Date MAJ Logo", max_length=200, blank=True, null=True)
    adresse_exp = models.ForeignKey(AdresseMail, verbose_name="Adresse d'expédition", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez une des adresses d'expédition d'emails dans la liste. Il est possible de créer de nouvelles adresses depuis le menu Paramétrage > Adresses d'expédition.")
    configuration_sms = models.ForeignKey(ConfigurationSMS, verbose_name="Configuration SMS", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez une configuration SMS dans la liste. Il est possible de créer de nouvelles configurations depuis le menu Paramétrage > Configurations SMS.")
    messagerie_active = models.BooleanField(verbose_name="Les familles sont autorisées à converser avec cette structure depuis la rubrique Contact du portail.", default=True)
    afficher_coords = models.BooleanField(verbose_name="Afficher les coordonnées de la structure sur le portail.", default=True)

    class Meta:
        db_table = 'structures'
        verbose_name = "structure"
        verbose_name_plural = "structures"

    def __str__(self):
        return self.nom


class SignatureEmail(models.Model):
    idsignature = models.AutoField(verbose_name="ID", db_column='IDsignature', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=250, help_text="Donnez un nom à cette signature pour la retrouver plus facilement.")
    html = models.TextField(verbose_name="Texte", blank=True, null=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True, help_text="Associez si besoin cette signature à une structure pour limiter son accès aux utilisateurs.")

    class Meta:
        db_table = 'signatures_emails'
        verbose_name = "signature d'email"
        verbose_name_plural = "signatures d'emails"

    def __str__(self):
        return self.nom if self.nom else "Nouvelle signature"


class CustomUserManager(UserManager):
    """ Permet d'ajouter au user le prefetch_related sur la table structures """
    def get(self, *args, **kwargs):
        return super().prefetch_related("structures").get(*args, **kwargs)

class Utilisateur(AbstractUser):
    categorie = models.CharField(verbose_name="Catégorie", max_length=50, blank=True, null=True, default="utilisateur")
    force_reset_password = models.BooleanField(verbose_name="Force la mise à jour du mot de passe", default=False)
    date_expiration_mdp = models.DateTimeField(verbose_name="Date d'expiration du mot de passe", blank=True, null=True)
    structures = models.ManyToManyField(Structure, verbose_name="Structures", related_name="utilisateur_structures", blank=True)
    adresse_exp = models.ForeignKey(AdresseMail, verbose_name="Adresse d'expédition d'emails", related_name="utilisateur_adresse_exp", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez une adresse d'expédition d'emails favorite dans la liste. Il est possible de créer de nouvelles adresses depuis le menu Paramétrage > Adresses d'expédition.")
    signature = models.ForeignKey(SignatureEmail, verbose_name="Signature d'emails", related_name="utilisateur_signature", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez une signature d'emails favorite dans la liste. Il est possible de créer de nouvelles signatures depuis le menu Paramétrage > Signatures d'emails.")
    objects = CustomUserManager()

    class Meta:
        permissions = utils_permissions.GetPermissionsPossibles()

    def Get_adresse_exp_defaut(self):
        # Renvoie l'adresse favorite
        if self.adresse_exp:
            return self.adresse_exp
        # Recherche une adresse parmi celles des structures
        for structure in self.structures.all():
            if structure.adresse_exp:
                return structure.adresse_exp
        return None

    def Get_configuration_sms_defaut(self):
        # Recherche une configuration SMS parmi celles des structures
        for structure in self.structures.all():
            if structure.configuration_sms:
                return structure.configuration_sms
        return None

    def Get_adresses_exp_possibles(self):
        liste_adresses_possibles = []
        if self.adresse_exp:
            liste_adresses_possibles.append(self.adresse_exp_id)
        for structure in self.structures.all():
            if structure.adresse_exp and structure.adresse_exp_id not in liste_adresses_possibles:
                liste_adresses_possibles.append(structure.adresse_exp_id)
        return liste_adresses_possibles

    def Get_configurations_sms_possibles(self):
        liste_configurations_possibles = []
        for structure in self.structures.all():
            if structure.configuration_sms and structure.configuration_sms_id not in liste_configurations_possibles:
                liste_configurations_possibles.append(structure.configuration_sms_id)
        return liste_configurations_possibles


class Assureur(models.Model):
    idassureur = models.AutoField(verbose_name="ID", db_column='IDassureur', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    rue_resid = models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True)
    cp_resid = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville_resid = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)
    telephone = models.CharField(verbose_name="Téléphone", max_length=200, blank=True, null=True)
    memo = models.TextField(verbose_name="Mémo", blank=True, null=True)

    class Meta:
        db_table = 'assureurs'
        verbose_name = "assureur"
        verbose_name_plural = "assureurs"

    def __str__(self):
        return self.nom

    def Get_nom(self, afficher_ville=False):
        texte = self.nom
        if afficher_ville and self.ville_resid:
            texte += " (%s)" % self.ville_resid
        return texte


class CategorieInformation(models.Model):
    idcategorie = models.AutoField(verbose_name="ID", db_column='IDcategorie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'categories_informations'
        verbose_name = "catégorie information"
        verbose_name_plural = "catégories informations"

    def __str__(self):
        return self.nom


class CategorieTravail(models.Model):
    idcategorie = models.AutoField(verbose_name="ID", db_column='IDcategorie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'categories_travail'
        verbose_name = "catégorie socio-professionnelle"
        verbose_name_plural = "catégories socio-professionnelles"

    def __str__(self):
        return self.nom


class CompteBancaire(models.Model):
    idcompte = models.AutoField(verbose_name="ID", db_column="IDcompte", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    numero = encrypt(models.CharField(verbose_name="Numéro", max_length=200, blank=True, null=True))
    defaut = models.BooleanField(verbose_name="Compte par défaut", default=False)
    raison = models.CharField(verbose_name="Raison sociale", max_length=200, blank=True, null=True)
    code_etab = models.CharField(verbose_name="Code établissement", max_length=200, blank=True, null=True)
    code_guichet = models.CharField(verbose_name="Code guichet", max_length=200, blank=True, null=True)
    code_nne = models.CharField(verbose_name="Code NNE", max_length=200, blank=True, null=True)
    cle_rib = models.CharField(verbose_name="Clé RIB", max_length=200, blank=True, null=True)
    cle_iban = models.CharField(verbose_name="Clé IBAN", max_length=200, blank=True, null=True)
    iban = encrypt(models.CharField(verbose_name="Numéro IBAN", max_length=200, blank=True, null=True))
    bic = encrypt(models.CharField(verbose_name="BIC", max_length=200, blank=True, null=True))
    code_ics = encrypt(models.CharField(verbose_name="Code ICS", max_length=200, blank=True, null=True))
    dft_titulaire = models.CharField(verbose_name="Titulaire DFT", max_length=400, blank=True, null=True)
    dft_iban = encrypt(models.CharField(verbose_name="IBAN DFT", max_length=400, blank=True, null=True))
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'comptes_bancaires'
        verbose_name = "compte bancaire"
        verbose_name_plural = "comptes bancaires"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(CompteBancaire.objects.filter(defaut=True)) == 0:
            objet = CompteBancaire.objects.first()
            if objet != None:
                objet.defaut = True
                objet.save()


class ModeReglement(models.Model):
    idmode = models.AutoField(verbose_name="ID", db_column="IDmode", primary_key=True)
    label = models.CharField(verbose_name="Nom", max_length=200)
    image = models.ImageField(verbose_name="Image", upload_to=get_uuid_path, blank=True, null=True)
    numero_choix = [(None, "Aucun"), ("ALPHA", "Alphanumérique"), ("NUM", "Numérique")]
    numero_piece = models.CharField(verbose_name="Numéro de pièce", max_length=100, choices=numero_choix, blank=True, null=True)
    nbre_chiffres = models.IntegerField(verbose_name="Nombre de caractères du numéro", blank=True, null=True)
    frais_choix = [(None, "Aucun"), ("LIBRE", "Montant libre"), ("FIXE", "Montant fixe"), ("PRORATA", "Montant au prorata")]
    frais_gestion = models.CharField(verbose_name="Frais de gestion", max_length=100, choices=frais_choix, blank=True, null=True)
    frais_montant = models.DecimalField(verbose_name="Montant fixe des frais", max_digits=10, decimal_places=2, blank=True, null=True)
    frais_pourcentage = models.DecimalField(verbose_name="Prorata des frais", max_digits=10, decimal_places=2, blank=True, null=True)
    arrondi_choix = [("centimesup", "Arrondi au centime supérieur"), ("centimeinf", "Arrondi au centime inférieur")]
    frais_arrondi = models.CharField(verbose_name="Méthode d'arrondi", max_length=100, choices=arrondi_choix, default="centimesup", blank=True, null=True)
    frais_label = models.CharField(verbose_name="Label de la prestation", max_length=200, blank=True, null=True)
    type_choix = [("banque", "Banque"), ("caisse", "Caisse")]
    type_comptable = models.CharField(verbose_name="Type comptable", max_length=100, choices=type_choix, default="banque", blank=True, null=True)
    code_compta = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'modes_reglements'
        verbose_name = "mode de règlement"
        verbose_name_plural = "modes de règlement"

    def __str__(self):
        return self.label


class Emetteur(models.Model):
    idemetteur = models.AutoField(verbose_name="ID", db_column='IDemetteur', primary_key=True)
    mode = models.ForeignKey(ModeReglement, verbose_name="Mode de règlement", on_delete=models.PROTECT)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    image = models.ImageField(verbose_name="Image", upload_to=get_uuid_path, blank=True, null=True)

    class Meta:
        db_table = 'emetteurs'
        verbose_name = "emetteur de règlement"
        verbose_name_plural = "emetteurs de règlement"

    def __str__(self):
        return self.nom



class Medecin(models.Model):
    idmedecin = models.AutoField(verbose_name="ID", db_column='IDmedecin', primary_key=True)
    nom = models.CharField(verbose_name=_("Nom"), max_length=200)
    prenom = models.CharField(verbose_name=_("Prénom"), max_length=200, blank=True, null=True)
    rue_resid = models.CharField(verbose_name=_("Rue"), max_length=200, blank=True, null=True)
    cp_resid = models.CharField(verbose_name=_("Code postal"), max_length=50, blank=True, null=True)
    ville_resid = models.CharField(verbose_name=_("Ville"), max_length=200, blank=True, null=True)
    tel_cabinet = models.CharField(verbose_name=_("Téléphone fixe"), max_length=200, blank=True, null=True)
    tel_mobile = models.CharField(verbose_name=_("Téléphone mobile"), max_length=200, blank=True, null=True)
    memo = models.TextField(verbose_name=_("Mémo"), blank=True, null=True)

    class Meta:
        db_table = 'medecins'
        verbose_name = "médecin"
        verbose_name_plural = "médecins"

    def __str__(self):
        return "%s %s" % (self.nom, self.prenom or "")

    def Get_nom(self, afficher_ville=False):
        texte = self.nom
        if self.prenom:
            texte += " " + self.prenom
        if afficher_ville and self.ville_resid:
            texte += " (%s)" % self.ville_resid
        return texte


class NiveauScolaire(models.Model):
    idniveau = models.AutoField(verbose_name="ID", db_column='IDniveau', primary_key=True)
    ordre = models.IntegerField(verbose_name="Ordre")
    nom = models.CharField(verbose_name="Nom", max_length=300)
    abrege = models.CharField(verbose_name="Abrégé", max_length=200)

    class Meta:
        db_table = 'niveaux_scolaires'
        verbose_name = "niveau scolaire"
        verbose_name_plural = "niveaux scolaires"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre des groupes
        liste_objects = NiveauScolaire.objects.all().order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1


class Organisateur(models.Model):
    """ Organisateur """
    idorganisateur = models.AutoField(verbose_name="ID", db_column="IDorganisateur", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200, null=True)
    rue = models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True)
    cp = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)
    tel = models.CharField(verbose_name="Téléphone", max_length=200, blank=True, null=True)
    fax = models.CharField(verbose_name="Fax", max_length=200, blank=True, null=True)
    mail = models.EmailField(verbose_name="Email", max_length=300, blank=True, null=True)
    site = models.CharField(verbose_name="Site internet", max_length=200, blank=True, null=True)
    num_agrement = models.CharField(verbose_name="Numéro d'agrément", max_length=200, blank=True, null=True)
    num_siret = models.CharField(verbose_name="Numéro SIRET", max_length=200, blank=True, null=True)
    code_ape = models.CharField(verbose_name="Code APE", max_length=200, blank=True, null=True)
    logo = ResizedImageField(verbose_name="Logo", upload_to=get_uuid_path, blank=True, null=True)
    gps = models.CharField(verbose_name="GPS", max_length=200, blank=True, null=True)
    logo_update = models.DateTimeField(verbose_name="Date MAJ Logo", max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'organisateur'
        verbose_name = "organisateur"
        verbose_name_plural = "organisateurs"

    def __str__(self):
        return self.nom



class Regime(models.Model):
    idregime = models.AutoField(verbose_name="ID", db_column='IDregime', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'regimes'
        verbose_name = "régime social"
        verbose_name_plural = "régimes sociaux"

    def __str__(self):
        return self.nom


class Caisse(models.Model):
    idcaisse = models.AutoField(verbose_name="ID", db_column='IDcaisse', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    regime = models.ForeignKey(Regime, verbose_name="Régime social", on_delete=models.PROTECT)

    class Meta:
        db_table = 'caisses'
        verbose_name = "caisse"
        verbose_name_plural = "caisses"

    def __str__(self):
        return self.nom


class TypePiece(models.Model):
    idtype_piece = models.AutoField(verbose_name="ID", db_column='IDtype_piece', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    public_choix = [("individu", "Individu"), ("famille", "Famille")]
    public = models.CharField(verbose_name="Public", max_length=50, choices=public_choix)
    duree_validite = models.CharField(verbose_name="Durée de validité", max_length=100, blank=True, null=True)
    valide_rattachement = models.BooleanField(verbose_name="Rattachement valide", default=False)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'types_pieces'
        verbose_name = "type de pièce"
        verbose_name_plural = "types de pièce"

    def __str__(self):
        return self.nom

    def Get_nom(self, individu=None):
        if self.public == "individu":
            prenom = individu.prenom or individu.nom
            return self.nom + " de " + prenom
        else:
            return self.nom

    def Get_duree(self):
        return utils_dates.ConvertDureeStrToDuree(self.duree_validite)

    def Get_date_fin_validite(self, date_reference=None):
        if not date_reference:
            date_reference = datetime.date.today()
        if not self.duree_validite:
            return datetime.date(2999, 1, 1)
        if self.duree_validite.startswith("j"):
            return date_reference + self.Get_duree()
        if self.duree_validite.startswith("d"):
            return utils_dates.ConvertDateENGtoDate(self.duree_validite[1:])


class TypeQuotient(models.Model):
    idtype_quotient = models.AutoField(verbose_name="ID", db_column='IDtype_quotient', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'types_quotients'
        verbose_name = "type de quotient"
        verbose_name_plural = "types de quotient"

    def __str__(self):
        return self.nom


class Vacance(models.Model):
    """ Périodes de vacances """
    idvacance = models.AutoField(verbose_name="ID", db_column="IDvacance", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200, choices=LISTE_VACANCES)
    annee = models.IntegerField(verbose_name="Année")
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")

    class Meta:
        db_table = 'vacances'
        verbose_name = "période de vacance"
        verbose_name_plural = "périodes de vacances"

    def __str__(self):
        return "%s %s" % (self.nom, self.annee)


class Ferie(models.Model):
    idferie = models.AutoField(verbose_name="ID", db_column="IDferie", primary_key=True)
    type_choix = [("fixe", "Fixe"), ("variable", "Variable")]
    type = models.CharField(verbose_name="Type", max_length=100, choices=type_choix)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    jour = models.IntegerField(verbose_name="Jour", validators=[MinValueValidator(1), MaxValueValidator(31)])
    mois = models.IntegerField(verbose_name="Mois")
    annee = models.IntegerField(verbose_name="Année", default=0)

    class Meta:
        db_table = 'jours_feries'
        verbose_name = "jour férié"
        verbose_name_plural = "jours fériés"

    def __str__(self):
        return "%s %d" % (self.nom, self.annee)


class Secteur(models.Model):
    idsecteur = models.AutoField(verbose_name="ID", db_column='IDsecteur', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'secteurs'
        verbose_name = "secteur géographique"
        verbose_name_plural = "secteurs géographiques"

    def __str__(self):
        return self.nom


class TypeMaladie(models.Model):
    idtype_maladie = models.AutoField(verbose_name="ID", db_column='IDtype_maladie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    vaccin_obligatoire = models.BooleanField(verbose_name="Vaccination obligatoire", default=False, help_text="Cochez cette case si la vaccination est obligatoire pour cette maladie.")
    vaccin_date_naiss_min = models.DateField(verbose_name="Date de naissance min.", blank=True, null=True, help_text="Si la vaccination n'est obligatoire que pour les individus nés à partir d'une date donnée, saisissez-là ici.")

    class Meta:
        db_table = 'types_maladies'
        verbose_name = "maladie"
        verbose_name_plural = "maladies"

    def __str__(self):
        return self.nom


class TypeSieste(models.Model):
    idtype_sieste = models.AutoField(verbose_name="ID", db_column='IDtype_sieste', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'types_sieste'
        verbose_name = "type de sieste"
        verbose_name_plural = "types de sieste"

    def __str__(self):
        return self.nom


class TypeVaccin(models.Model):
    idtype_vaccin = models.AutoField(verbose_name="ID", db_column='IDtype_vaccin', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    duree_validite = models.CharField(verbose_name="Durée de validité", max_length=100, blank=True, null=True)
    types_maladies = models.ManyToManyField(TypeMaladie, related_name="vaccin_maladies")

    class Meta:
        db_table = 'types_vaccins'
        verbose_name = "vaccin"
        verbose_name_plural = "vaccins"

    def __str__(self):
        return self.nom



class Ecole(models.Model):
    idecole = models.AutoField(verbose_name="ID", db_column='IDecole', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    rue = models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True)
    cp = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)
    tel = models.CharField(verbose_name="Téléphone", max_length=200, blank=True, null=True)
    fax = models.CharField(verbose_name="Fax", max_length=200, blank=True, null=True)
    mail = models.EmailField(verbose_name="Email", max_length=300, blank=True, null=True)
    secteurs = models.ManyToManyField(Secteur, blank=True, related_name="ecole_secteurs")

    class Meta:
        db_table = 'ecoles'
        verbose_name = "école"
        verbose_name_plural = "écoles"

    def __str__(self):
        return self.nom


class Classe(models.Model):
    idclasse = models.AutoField(verbose_name="ID", db_column='IDclasse', primary_key=True)
    ecole = models.ForeignKey(Ecole, verbose_name="Ecole", on_delete=models.PROTECT)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    niveaux = models.ManyToManyField(NiveauScolaire, related_name="classe_niveaux")

    class Meta:
        db_table = 'classes'
        verbose_name = "classe"
        verbose_name_plural = "classes"

    def __str__(self):
        return self.nom


class TypeCotisation(models.Model):
    idtype_cotisation = models.AutoField(verbose_name="ID", db_column='IDtype_cotisation', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    type_cotisation = [("famille", "Familiale"), ("individu", "Individuelle")]
    type = models.CharField(verbose_name="Type", max_length=100, choices=type_cotisation, default="famille")
    carte = models.BooleanField(verbose_name="Carte d'adhérent", default=False)
    code_comptable = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    code_analytique = models.CharField(verbose_name="Code analytique", max_length=200, blank=True, null=True)
    code_produit_local = models.CharField(verbose_name="Code produit local", max_length=200, blank=True, null=True)
    defaut = models.BooleanField(verbose_name="Type par défaut", default=False)
    activite = models.ForeignKey("Activite", verbose_name="Activité associée", on_delete=models.PROTECT, blank=True, null=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'types_cotisations'
        verbose_name = "type d'adhésion"
        verbose_name_plural = "types d'adhésions"

    def __str__(self):
        return self.nom


class UniteCotisation(models.Model):
    idunite_cotisation = models.AutoField(verbose_name="ID", db_column='IDunite_cotisation', primary_key=True)
    type_cotisation = models.ForeignKey(TypeCotisation, verbose_name="Type d'adhésion", on_delete=models.PROTECT)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    date_debut = models.DateField(verbose_name="Date de début", blank=True, null=True)
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    duree = models.CharField(verbose_name="Durée", max_length=200, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    label_prestation = models.CharField(verbose_name="Label de la prestation", max_length=200, blank=True, null=True)
    defaut = models.BooleanField(verbose_name="Unité par défaut", default=False)
    tarifs = models.TextField(verbose_name="Tarifs", blank=True, null=True)
    prefacturation = models.BooleanField(verbose_name="Activer la préfacturation pour cette unité", default=False, help_text="Cochez cette case pour que la famille puisse payer cette unité d'adhésion sur le portail même si aucune facture n'a été générée.")

    class Meta:
        db_table = 'unites_cotisations'
        verbose_name = "unité d'adhésion"
        verbose_name_plural = "unités d'adhésion"

    def __str__(self):
        return self.nom

    def Get_duree(self):
        return utils_dates.ConvertDureeStrToDuree(self.duree)

    def Get_dates_validite(self, date_debut=None):
        if self.duree == None:
            return (self.date_debut, self.date_fin)
        else:
            if date_debut == None:
                date_debut = datetime.date.today()
            return (date_debut, date_debut + self.Get_duree())

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(UniteCotisation.objects.filter(defaut=True)) == 0:
            objet = UniteCotisation.objects.first()
            if objet != None:
                objet.defaut = True
                objet.save()


class NoteCategorie(models.Model):
    idcategorie = models.AutoField(verbose_name="ID", db_column='IDcategorie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    choix_priorite = [("NORMALE", "Normale"), ("HAUTE", "Haute")]
    priorite = models.CharField(verbose_name="Priorité", max_length=100, choices=choix_priorite, default="NORMALE")
    afficher_accueil = models.BooleanField(verbose_name="Afficher sur la page d'accueil", default=False)
    afficher_liste = models.BooleanField(verbose_name="Afficher sur la liste des consommations", default=False)

    class Meta:
        db_table = 'notes_categories'
        verbose_name = "catégorie de note"
        verbose_name_plural = "catégories de note"

    def __str__(self):
        return self.nom


class ListeDiffusion(models.Model):
    idliste = models.AutoField(verbose_name="ID", db_column='IDliste', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)

    class Meta:
        db_table = 'listes_diffusion'
        verbose_name = "liste de diffusion"
        verbose_name_plural = "listes de diffusion"

    def __str__(self):
        return self.nom


class RegimeAlimentaire(models.Model):
    idtype_regime = models.AutoField(verbose_name="ID", db_column='IDtype_regime', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)

    class Meta:
        db_table = 'regimes_alimentaires'
        verbose_name = "régime alimentaire"
        verbose_name_plural = "régimes alimentaires"

    def __str__(self):
        return self.nom


class Restaurateur(models.Model):
    idrestaurateur = models.AutoField(verbose_name="ID", db_column='IDrestaurateur', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    rue = models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True)
    cp = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)
    tel = models.CharField(verbose_name="Téléphone", max_length=200, blank=True, null=True)
    fax = models.CharField(verbose_name="Fax", max_length=200, blank=True, null=True)
    mail = models.EmailField(verbose_name="Email", max_length=300, blank=True, null=True)

    class Meta:
        db_table = 'restaurateurs'
        verbose_name = "restaurateur"
        verbose_name_plural = "restaurateurs"

    def __str__(self):
        return self.nom


class MenuCategorie(models.Model):
    idcategorie = models.AutoField(verbose_name="ID", db_column='IDcategorie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    ordre = models.IntegerField(verbose_name="Ordre")

    class Meta:
        db_table = 'menus_categories'
        verbose_name = "catégorie de menu"
        verbose_name_plural = "catégories de menu"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre des groupes
        liste_objects = MenuCategorie.objects.all().order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1


class MenuLegende(models.Model):
    idlegende = models.AutoField(verbose_name="ID", db_column='IDlegende', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    couleur = models.CharField(verbose_name="Couleur", max_length=100)

    class Meta:
        db_table = 'menus_legendes'
        verbose_name = "légende de menu"
        verbose_name_plural = "légendes de menu"

    def __str__(self):
        return self.nom


class CategorieProduit(models.Model):
    idcategorie = models.AutoField(verbose_name="ID", db_column='IDcategorie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    image = models.ImageField(verbose_name="Image", upload_to=get_uuid_path, blank=True, null=True)

    class Meta:
        db_table = 'produits_categories'
        verbose_name = "Catégorie de produits"
        verbose_name_plural = "Catégories de produits"

    def __str__(self):
        return self.nom


class Produit(models.Model):
    idproduit = models.AutoField(verbose_name="ID", db_column='IDproduit', primary_key=True)
    categorie = models.ForeignKey(CategorieProduit, verbose_name="Catégorie", on_delete=models.PROTECT)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    image = models.ImageField(verbose_name="Image", upload_to=get_uuid_path, blank=True, null=True)
    quantite = models.IntegerField(verbose_name="Quantité", default=1)
    montant = models.DecimalField(verbose_name="Montant", blank=True, null=True, max_digits=10, decimal_places=2, default=0.0)
    couleur = models.CharField(verbose_name="Couleur", max_length=100, default="#3c8dbc")

    class Meta:
        db_table = "produits"
        verbose_name = "produit"
        verbose_name_plural = "produits"

    def __str__(self):
        return self.nom


class TarifProduit(models.Model):
    idtarif = models.AutoField(verbose_name="ID", db_column='IDtarif', primary_key=True)
    produit = models.ForeignKey(Produit, verbose_name="Produit", on_delete=models.CASCADE)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    description = models.CharField(verbose_name="Description", max_length=400, blank=True, null=True)
    observations = models.CharField(verbose_name="Observations", max_length=400, blank=True, null=True)
    tva = models.DecimalField(verbose_name="Taux TVA", max_digits=10, decimal_places=2, blank=True, null=True)
    label_prestation = models.CharField(verbose_name="Label de la prestation", max_length=300, blank=True, null=True)
    code_compta = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    choix_methode = [("produit_montant_unique", "Montant unique"), ("produit_proportionnel_quantite", "Montant proportionnel à la quantité")]
    methode = models.CharField(verbose_name="Méthode", max_length=200, choices=choix_methode, default="montant_unique")
    montant = models.DecimalField(verbose_name="Montant", blank=True, null=True, max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'produits_tarifs'
        verbose_name = "tarif de produit"
        verbose_name_plural = "tarifs de produit"

    def __str__(self):
        return "Tarif de produit ID%d" % self.idtarif if self.idtarif else "Nouveau tarif"


class TypeGroupeActivite(models.Model):
    idtype_groupe_activite = models.AutoField(verbose_name="ID", db_column='IDtype_groupe_activite', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    observations = models.CharField(verbose_name="Observations", max_length=300, blank=True, null=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT)

    class Meta:
        db_table = 'types_groupes_activites'
        verbose_name = "groupe d'activités"
        verbose_name_plural = "groupes d'activités"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Avant la suppression
        if Activite.objects.filter(groupes_activites__in=[self]).count() > 0:
            return "La suppression de '%s' est impossible car ce groupe d'activités est déjà associé à au moins une activité" % self
        # Supprime l'objet
        super().delete(*args, **kwargs)


class FactureRegie(models.Model):
    idregie = models.AutoField(verbose_name="ID", db_column='IDregie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    numclitipi = models.CharField(verbose_name="Numéro de client TIPI", max_length=300)
    email_regisseur = models.EmailField(verbose_name="Email du régisseur", max_length=300)
    compte_bancaire = models.ForeignKey(CompteBancaire, verbose_name="Compte bancaire associé", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'factures_regies'
        verbose_name = "régie"
        verbose_name_plural = "régies"

    def __str__(self):
        return self.nom


class TypeConsentement(models.Model):
    idtype_consentement = models.AutoField(verbose_name="ID", db_column='IDtype_consentement', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200, help_text="Il s'agit généralement d'un nom du document. Exemple : Règlement intérieur de la structure...")
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'types_consentements'
        verbose_name = "type de consentement"
        verbose_name_plural = "types de consentements"

    def __str__(self):
        return self.nom


class UniteConsentement(models.Model):
    idunite_consentement = models.AutoField(verbose_name="ID", db_column='IDunite_consentement', primary_key=True)
    type_consentement = models.ForeignKey(TypeConsentement, verbose_name="type de consentement", on_delete=models.PROTECT)
    date_debut = models.DateField(verbose_name="Date de début", help_text="Saisissez la date de début d'application de cette unité. Par défaut la date du jour.")
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True, help_text="La date de fin n'est généralement pas utilisée sauf si le document n'est applicable que sur une période donnée.")
    document = models.FileField(verbose_name="Document", upload_to=get_uuid_path, blank=True, null=True, help_text="Privilégiez un document au format PDF.")

    class Meta:
        db_table = 'unites_consentements'
        verbose_name = "unité de consentement"
        verbose_name_plural = "unités de consentements"

    def __str__(self):
        return "Unité de consentement ID%s" % self.idunite_consentement

    def get_upload_path(self):
        return str(self.type_consentement_id)

    def Get_extension(self):
        return os.path.splitext(self.document.name)[1].replace(".", "")


class Activite(models.Model):
    idactivite = models.AutoField(verbose_name="ID", db_column='IDactivite', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    abrege = models.CharField(verbose_name="Abrégé", max_length=100)
    coords_org = models.BooleanField(verbose_name="Coordonnées identiques à celles de l'organisateur", default=True)
    rue = models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True)
    cp = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)
    tel = models.CharField(verbose_name="Téléphone", max_length=200, blank=True, null=True)
    fax = models.CharField(verbose_name="Fax", max_length=200, blank=True, null=True)
    mail = models.EmailField(verbose_name="Email", max_length=300, blank=True, null=True)
    site = models.CharField(verbose_name="site internet", max_length=300, blank=True, null=True)
    logo_org = models.BooleanField(verbose_name="Logo identique à celui de l'organisateur", default=True)
    logo = ResizedImageField(verbose_name="Logo", upload_to=get_uuid_path, blank=True, null=True)
    pay_org = models.BooleanField(verbose_name="Activation paiement par lien externe", default=True)
    pay = models.CharField(verbose_name="URL complet de paiement", max_length=200, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début", blank=True, null=True)
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    # public = models.CharField(blank=True, null=True)
    vaccins_obligatoires = models.BooleanField(verbose_name="Vaccinations obligatoires", default=False)
    assurance_obligatoire = models.BooleanField(verbose_name="Assurance obligatoire", default=False)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    nbre_inscrits_max = models.IntegerField(verbose_name="Nombre d'inscrits maximal", blank=True, null=True)
    code_comptable = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    code_analytique = models.CharField(verbose_name="Code analytique", max_length=200, blank=True, null=True)
    # psu_activation = models.IntegerField(blank=True, null=True)
    # psu_unite_prevision = models.IntegerField(blank=True, null=True)
    # psu_unite_presence = models.IntegerField(blank=True, null=True)
    # psu_tarif_forfait = models.IntegerField(blank=True, null=True)
    # psu_etiquette_rtt = models.IntegerField(blank=True, null=True)
    choix_affichage_inscriptions = [("JAMAIS", "Ne pas autoriser"), ("TOUJOURS", "Autoriser"), ("PERIODE", "Autoriser sur la période suivante")]
    portail_inscriptions_affichage = models.CharField(verbose_name="Inscriptions autorisées", max_length=100, choices=choix_affichage_inscriptions, default="JAMAIS")
    portail_inscriptions_date_debut = models.DateTimeField(verbose_name="Date de début d'affichage", blank=True, null=True)
    portail_inscriptions_date_fin = models.DateTimeField(verbose_name="Date de fin d'affichage", blank=True, null=True)
    portail_inscriptions_imposer_pieces = models.BooleanField(verbose_name="Imposer le téléchargement des pièces à fournir", default=False)
    portail_inscriptions_bloquer_si_complet = models.BooleanField(verbose_name="Empêcher l'inscription si activité complète", default=False)
    choix_affichage_reservations = [("JAMAIS", "Ne pas autoriser"), ("TOUJOURS", "Autoriser")]
    portail_reservations_affichage = models.CharField(verbose_name="Réservations autorisées", max_length=100, choices=choix_affichage_reservations, default="JAMAIS")
    portail_reservations_limite = models.CharField(verbose_name="Date limite de modification d'une réservation", max_length=200, blank=True, null=True)
    # portail_reservations_absenti = models.CharField(verbose_name="Application d'une absence injustifiée", max_length=200, blank=True, null=True)
    # portail_unites_multiples = models.BooleanField(verbose_name="Sélection multiple d'unités autorisée", default=False)
    choix_affichage_dates_passees = [("0", "Jamais"), ("2", "Deux jours"), ("3", "Trois jours"), ("7", "Une semaine"), ("14", "Deux semaines"), ("30", "Un mois"), ("61", "Deux mois"), ("92", "Trois mois"), ("9999", "Toujours")]
    portail_afficher_dates_passees = models.CharField(verbose_name="Afficher les dates passées", max_length=100, choices=choix_affichage_dates_passees, default="0")
    regie = models.ForeignKey(FactureRegie, verbose_name="Régie de facturation", on_delete=models.PROTECT, blank=True, null=True)
    groupes_activites = models.ManyToManyField(TypeGroupeActivite, blank=True, related_name="activite_groupes_activites")
    pieces = models.ManyToManyField(TypePiece, verbose_name="Types de pièces", related_name="activite_types_pieces", blank=True, help_text="Sélectionnez dans la liste les types de pièces qui doivent être à jour.")
    cotisations = models.ManyToManyField(TypeCotisation, verbose_name="Types d'adhésions", related_name="activite_types_cotisations", blank=True, help_text="Sélectionnez dans la liste des types d'adhésions qui doivent être à jour.")
    types_consentements = models.ManyToManyField(TypeConsentement, verbose_name="Types de consentements", related_name="activite_types_consentements", blank=True, help_text="Sélectionnez dans la liste les types de consentements internet nécessaires.")
    inscriptions_multiples = models.BooleanField(verbose_name="Autoriser plusieurs inscriptions simultanées pour chaque individu", default=False)
    code_produit_local = models.CharField(verbose_name="Code produit local", max_length=200, blank=True, null=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT)
    service1 = models.CharField(verbose_name="Service axe 1", max_length=15, blank=True, null=True, help_text="Premier axe analytique.")
    service2 = models.CharField(verbose_name="Service axe 2", max_length=10, blank=True, null=True, help_text="Second axe analytique.")
    reattribution_auto = models.BooleanField(verbose_name="Réattribution automatique des places disponibles", default=False, help_text="Cochez cette case pour laisser Noethysweb réattribuer les places en attente automatiquement chaque nuit.")
    reattribution_adresse_exp = models.ForeignKey(AdresseMail, verbose_name="Adresse d'expédition", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez l'adresse d'expédition d'emails qui sera utilisée pour envoyer une notification de réattribution de places à la famille.")
    reattribution_delai = models.IntegerField(verbose_name="Délai de réattribution", blank=True, null=True, choices=[(1, "1 jour"), (2, "2 jours"), (3, "3 jours"), (4, "4 jours"), (5, "5 jours"), (7, "1 semaine"), (14, "2 semaines")], default=2, help_text="Sélectionnez le nombre de jours jusqu'auquel il est possible de réattribuer des places.")
    reattribution_modele_email = models.ForeignKey("ModeleEmail", verbose_name="Modèle d'Email", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez le modèle d'email qui sera utilisé pour notifier les familles par email de la réattribution.")

    class Meta:
        db_table = 'activites'
        verbose_name = "activité"
        verbose_name_plural = "activités"

    def __str__(self):
        return self.nom

    def Get_validite_str(self):
        if not self.date_fin or self.date_fin.year == 2999:
            return "Illimitée"
        else:
            return "Du %s au %s" % (utils_dates.ConvertDateToFR(self.date_debut), utils_dates.ConvertDateToFR(self.date_fin))

    def Get_groupes(self):
        return Groupe.objects.filter(activite=self).order_by("ordre")

    def Get_unites(self):
        return Unite.objects.filter(activite=self).order_by("ordre")

    def Get_agrement(self, date=None):
        for agrement in Agrement.objects.filter(activite=self).order_by("date_debut"):
            if agrement.date_debut <= date <= agrement.date_fin:
                return agrement.agrement
        return None

class ResponsableActivite(models.Model):
    idresponsable = models.AutoField(verbose_name="ID", db_column='IDresponsable', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    choix_sexe = [("H", "Homme"), ("F", "Femme")]
    sexe = models.CharField(verbose_name="Sexe", max_length=50, choices=choix_sexe, default="H")
    nom = models.CharField(verbose_name="Nom et prénom", max_length=300)
    fonction = models.CharField(verbose_name="Fonction", max_length=300, blank=True, null=True)
    defaut = models.BooleanField(verbose_name="Responsable par défaut", default=False)

    class Meta:
        db_table = 'responsables_activite'
        verbose_name = "responsable d'activité"
        verbose_name_plural = "responsables d'activité"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(ResponsableActivite.objects.filter(activite=self.activite, defaut=True)) == 0:
            objet = ResponsableActivite.objects.filter(activite=self.activite).first()
            if objet != None:
                objet.defaut = True
                objet.save()


class Agrement(models.Model):
    idagrement = models.AutoField(verbose_name="ID", db_column='IDagrement', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    agrement = models.CharField(verbose_name="Agrément", max_length=200)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")

    class Meta:
        db_table = 'agrements'
        verbose_name = "agrément"
        verbose_name_plural = "agréments"

    def __str__(self):
        return self.agrement


class Groupe(models.Model):
    idgroupe = models.AutoField(verbose_name="ID", db_column='IDgroupe', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    abrege = models.CharField(verbose_name="Abrégé", max_length=200, blank=True, null=True)
    ordre = models.IntegerField(verbose_name="Ordre")
    nbre_inscrits_max = models.IntegerField(verbose_name="Nombre d'inscrits maximal", blank=True, null=True)

    class Meta:
        db_table = 'groupes'
        verbose_name = "groupe"
        verbose_name_plural = "groupes"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre des groupes
        liste_objects = Groupe.objects.filter(activite=self.activite).order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1


class Unite(models.Model):
    idunite = models.AutoField(verbose_name="ID", db_column='IDunite', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    ordre = models.IntegerField(verbose_name="Ordre")
    nom = models.CharField(verbose_name="Nom", max_length=200)
    abrege = models.CharField(verbose_name="Abrégé", max_length=200)
    choix_type = [("Unitaire", "Unitaire"), ("Horaire", "Horaire"), ('Quantite', 'Quantité'), ('Multihoraires', 'Multihoraires'), ('Evenement', 'Evénementiel')]
    type = models.CharField(verbose_name="Type", max_length=100, choices=choix_type, default="Unitaire")
    heure_debut = models.TimeField(verbose_name="Heure de début", blank=True, null=True)
    heure_debut_fixe = models.BooleanField(verbose_name="Heure de début fixe", default=False)
    heure_fin = models.TimeField(verbose_name="Heure de fin", blank=True, null=True)
    heure_fin_fixe = models.BooleanField(verbose_name="Heure de fin fixe", default=False)
    heure_debut_min = models.TimeField(verbose_name="Heure de début min.", blank=True, null=True)
    heure_debut_max = models.TimeField(verbose_name="Heure de début max.", blank=True, null=True)
    heure_fin_min = models.TimeField(verbose_name="Heure de fin min.", blank=True, null=True)
    heure_fin_max = models.TimeField(verbose_name="Heure de fin max.", blank=True, null=True)
    repas = models.BooleanField(verbose_name="Repas inclus", default=False)
    restaurateur = models.ForeignKey(Restaurateur, verbose_name="Restaurateur", blank=True, null=True, on_delete=models.CASCADE)
    date_debut = models.DateField(verbose_name="Date de début de validité", blank=True, null=True)
    date_fin = models.DateField(verbose_name="Date de fin de validité", blank=True, null=True)
    choix_touches = [("WXK_TAB", "Tabulation"), ("WXK_SHIFT", "Shift"), ('WXK_ALT', 'Alt'), ('WXK_CONTROL', 'Control'), ('WXK_SPACE', 'Barre espace'),
                     ("WXK_F1", "F1"), ("WXK_F2", "F2"), ('WXK_F3', 'F3'), ('WXK_F4', 'F4'), ('WXK_F5', 'F5'), ('WXK_F6', 'F6'), ('WXK_F7', 'F7'),
                     ("WXK_F8", "F8"), ("WXK_F9", "F9"), ('WXK_F10', 'F10'), ('WXK_F11', 'F11'), ('WXK_F12', 'F12')]
    touche_raccourci = models.CharField(verbose_name="Touche raccourci", max_length=50, choices=choix_touches, blank=True, null=True)
    largeur = models.IntegerField(verbose_name="Largeur de la colonne", default=50)
    coeff = models.CharField(verbose_name="Coefficient pour l'état global", max_length=200, blank=True, null=True)
    autogen_active = models.BooleanField(verbose_name="Activer l'auto-génération", default=False)
    autogen_conditions = models.CharField(verbose_name="Conditions de la génération", max_length=400, blank=True, null=True)
    autogen_parametres = models.CharField(verbose_name="Paramètres de la génération", max_length=400, blank=True, null=True)
    groupes = models.ManyToManyField(Groupe, blank=True)
    incompatibilites = models.ManyToManyField("self", verbose_name="Incompatibilités", blank=True)
    visible_portail = models.BooleanField(verbose_name="Visible sur le portail", default=True)
    imposer_saisie_valeur = models.BooleanField(verbose_name="Imposer la saisie de la valeur aux usagers sur le portail (uniquement pour les unités de type horaire ou quantité)", default=False)
    equiv_journees = models.FloatField(verbose_name="Equivalence en journées", blank=True, null=True)
    equiv_heures = models.TimeField(verbose_name="Equivalence en heures", blank=True, null=True)
    dependances = models.ManyToManyField("self", verbose_name="Unités liées", blank=True, symmetrical=False)

    class Meta:
        db_table = 'unites'
        verbose_name = "unité de consommation"
        verbose_name_plural = "unités de consommation"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre des unités
        liste_objects = Unite.objects.filter(activite=self.activite).order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1



class UniteRemplissage(models.Model):
    idunite_remplissage = models.AutoField(verbose_name="ID", db_column='IDunite_remplissage', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    ordre = models.IntegerField(verbose_name="Ordre")
    nom = models.CharField(verbose_name="Nom", max_length=200, help_text="Renseigner le nom complet de l'unité. Exemples : Journée, Matinée, Séance, Atelier...")
    abrege = models.CharField(verbose_name="Abrégé", max_length=200, help_text="Le nom abrégé est généralement constitué de quelques caractères en majuscules. Exemples : J, M, SEANCE, ATELIER...")
    date_debut = models.DateField(verbose_name="Date de début de validité", blank=True, null=True)
    date_fin = models.DateField(verbose_name="Date de fin de validité", blank=True, null=True)
    seuil_alerte = models.IntegerField(verbose_name="Seuil d'alerte", default=5, help_text="Nombre de places restantes à partir duquel il faut colorer le fond de la case en jaune. Valeur conseillée : 5.")
    heure_min = models.TimeField(verbose_name="Heure min", blank=True, null=True)
    heure_max = models.TimeField(verbose_name="Heure max", blank=True, null=True)
    afficher_page_accueil = models.BooleanField(verbose_name="Afficher dans les effectifs de la page d'accueil", default=True)
    afficher_grille_conso = models.BooleanField(verbose_name="Afficher dans la grille des consommations", default=True)
    # etiquettes = models.CharField(blank=True, null=True)
    largeur = models.IntegerField(verbose_name="Largeur de la colonne", blank=True, null=True)
    unites = models.ManyToManyField(Unite, verbose_name="Unités associées", related_name="unite_remplissage_unites")

    class Meta:
        db_table = 'unites_remplissage'
        verbose_name = "unité de remplissage"
        verbose_name_plural = "unités de remplissage"

    def __str__(self):
        return self.nom

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre des unités
        liste_objects = UniteRemplissage.objects.filter(activite=self.activite).order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1


class Evenement(models.Model):
    idevenement = models.AutoField(verbose_name="ID", db_column='IDevenement', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    unite = models.ForeignKey(Unite, verbose_name="Unité de consommation", on_delete=models.CASCADE)
    groupe = models.ForeignKey(Groupe, verbose_name="Groupe", on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Date")
    nom = models.CharField(verbose_name="Nom", max_length=200)
    description = models.CharField(verbose_name="Description", max_length=400, blank=True, null=True)
    capacite_max = models.IntegerField(verbose_name="Capacité max.", blank=True, null=True)
    heure_debut = models.TimeField(verbose_name="Heure de début", blank=True, null=True)
    heure_fin = models.TimeField(verbose_name="Heure de fin", blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", blank=True, null=True, max_digits=10, decimal_places=2, default=0.0)
    equiv_heures = models.TimeField(verbose_name="Equivalence en heures", blank=True, null=True)

    class Meta:
        db_table = 'evenements'
        verbose_name = "événement"
        verbose_name_plural = "événements"

    def __str__(self):
        return "Evenement ID%d" % self.idevenement


class CategorieTarif(models.Model):
    idcategorie_tarif = models.AutoField(verbose_name="ID", db_column='IDcategorie_tarif', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'categories_tarifs'
        verbose_name = "catégorie de tarif"
        verbose_name_plural = "catégories de tarif"

    def __str__(self):
        return self.nom


class NomTarif(models.Model):
    idnom_tarif = models.AutoField(verbose_name="ID", db_column='IDnom_tarif', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    nom = models.CharField(verbose_name="Nom", max_length=300)

    class Meta:
        db_table = 'noms_tarifs'
        verbose_name = "nom de tarif"
        verbose_name_plural = "noms de tarif"

    def __str__(self):
        return self.nom


class Tarif(models.Model):
    idtarif = models.AutoField(verbose_name="ID", db_column='IDtarif', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    choix_type = [("JOURN", "Prestation journalière"), ("FORFAIT", "Forfait daté"), ("CREDIT", "Forfait crédit"), ("BAREME", "Barême de contrat"), ("EVENEMENT", "Evénement")]
    type = models.CharField(verbose_name="Type", max_length=100, choices=choix_type, default="JOURN")
    nom_tarif = models.ForeignKey(NomTarif, verbose_name="Nom de tarif", blank=True, null=True, on_delete=models.CASCADE)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    # condition_nbre_combi = models.IntegerField(blank=True, null=True)
    # condition_periode = models.CharField(blank=True, null=True)
    # condition_nbre_jours = models.IntegerField(blank=True, null=True)
    # condition_conso_facturees = models.IntegerField(blank=True, null=True)
    # condition_dates_continues = models.IntegerField(blank=True, null=True)
    forfait_saisie_manuelle = models.BooleanField(verbose_name="Ce forfait peut être saisi manuellement depuis la grille des consommations", default=False)
    forfait_saisie_auto = models.BooleanField(verbose_name="Ce forfait est automatiquement créé lors de l'inscription à l'activité", default=False)
    forfait_suppression_auto = models.BooleanField(verbose_name="Ce forfait ne peut être supprimé que lors de la désinscription à l'activité", default=False)
    choix_methode = [(dict_methode["code"], dict_methode["label"]) for dict_methode in LISTE_METHODES_TARIFS]
    methode = models.CharField(verbose_name="Méthode", max_length=200, choices=choix_methode, default="montant_unique")
    forfait_duree = models.CharField(verbose_name="Durée de validité par défaut", max_length=100, blank=True, null=True)
    beneficiaire_choix = [("individu", "Forfait individuel"), ("famille", "Forfait familial")]
    forfait_beneficiaire = models.CharField(verbose_name="Type de forfait", max_length=50, choices=beneficiaire_choix, default="individu", blank=True, null=True)
    description = models.CharField(verbose_name="Description", max_length=400, blank=True, null=True)
    jours_scolaires = MultiSelectField(verbose_name="Jours sur les périodes scolaires", max_length=100, choices=JOURS_SEMAINE, blank=True, null=True)
    jours_vacances = MultiSelectField(verbose_name="Jours sur les périodes de vacances", max_length=100, choices=JOURS_SEMAINE, blank=True, null=True)
    options = models.CharField(verbose_name="Options", max_length=450, blank=True, null=True)
    observations = models.CharField(verbose_name="Observations", max_length=400, blank=True, null=True)
    tva = models.DecimalField(verbose_name="Taux TVA", max_digits=10, decimal_places=2, blank=True, null=True)
    code_compta = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    date_facturation = models.CharField(verbose_name="Date de facturation", max_length=200, blank=True, null=True)
    # etiquettes = models.CharField(blank=True, null=True)
    etats = MultiSelectField(verbose_name="Etats conditionnels", max_length=200, choices=LISTE_ETATS_CONSO, blank=True, null=True)
    label_prestation = models.CharField(verbose_name="Label de la prestation", max_length=300, blank=True, null=True)
    evenement = models.ForeignKey(Evenement, verbose_name="Evénement", blank=True, null=True, on_delete=models.CASCADE)
    produit = models.ForeignKey(Produit, verbose_name="Produit", blank=True, null=True, on_delete=models.CASCADE)
    categories_tarifs = models.ManyToManyField(CategorieTarif, verbose_name="Catégories de tarifs", related_name="tarif_categories_tarifs")
    groupes = models.ManyToManyField(Groupe, verbose_name="Groupes", blank=True, related_name="tarif_groupes")
    cotisations = models.ManyToManyField(TypeCotisation, verbose_name="Cotisations", blank=True, related_name="tarif_cotisations")
    caisses = models.ManyToManyField(Caisse, verbose_name="Caisses", blank=True, related_name="tarif_caisses")
    type_quotient = models.ForeignKey(TypeQuotient, verbose_name="Type de QF", blank=True, null=True, on_delete=models.CASCADE, help_text="Sélectionnez un type de quotient familial ou laissez le champ vide pour tenir compte de tous les types de quotients.")
    facturation_unite = models.BooleanField(verbose_name="Facturation par unité horaire", default=False, help_text="Le montant par unité horaire et la quantité seront mémorisés dans la prestation.")
    choix_penalite = [(None, "Aucune"), ("pourcentage", "Pourcentage du montant dû")]
    penalite = models.CharField(verbose_name="Pénalité", max_length=100, choices=choix_penalite, default=None, blank=True, null=True, help_text="Sélectionnez un type de pénalité financière à appliquer en cas d'absence injustifiée.")
    penalite_pourcentage = models.DecimalField(verbose_name="Pourcentage", max_digits=10, decimal_places=2, default=100, blank=True, null=True, help_text="Saisissez le pourcentage à appliquer.")
    penalite_label = models.CharField(verbose_name="Label de la prestation", max_length=300, blank=True, null=True, help_text="Saisissez le label de la prestation de pénalité. Laissez vide pour utiliser le label par défaut. Mots-clés disponibles : {LABEL_PRESTATION}.")

    class Meta:
        db_table = 'tarifs'
        verbose_name = "tarif"
        verbose_name_plural = "tarifs"

    def __str__(self):
        return "Tarif ID%d - %s - à partir du %s" % (self.idtarif, self.nom_tarif.nom, self.date_debut.strftime("%d/%m/%Y")) if self.idtarif else "Nouveau tarif"


class ModelePrestation(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column='IDmodele', primary_key=True)
    categorie_choix = [("cotisation", "Adhésion"), ("consommation", "Consommation"), ("autre", "Autre")]
    categorie = models.CharField(verbose_name="Catégorie", max_length=100, choices=categorie_choix, default="autre")
    label = models.CharField(verbose_name="Label", max_length=200)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.SET_NULL, blank=True, null=True)
    tarif = models.ForeignKey(Tarif, verbose_name="Tarif", on_delete=models.SET_NULL, blank=True, null=True)
    categorie_tarif = models.ForeignKey(CategorieTarif, verbose_name="Catégorie de tarif", on_delete=models.SET_NULL, blank=True, null=True)
    tva = models.DecimalField(verbose_name="Taux de TVA", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    code_compta = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    public_choix = [("individu", "Individu"), ("famille", "Famille")]
    public = models.CharField(verbose_name="Public", max_length=50, choices=public_choix)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    tarifs = models.TextField(verbose_name="Tarifs", blank=True, null=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)
    # type_quotient = models.ForeignKey(TypeQuotient, verbose_name="Type de QF", blank=True, null=True, on_delete=models.SET_NULL, help_text="Sélectionnez un type de quotient familial ou laissez le champ vide pour tenir compte de tous les types de quotients.")

    class Meta:
        db_table = 'modeles_prestations'
        verbose_name = "modèle de prestation"
        verbose_name_plural = "modèles de prestations"

    def __str__(self):
        return "Modèle de prestation ID%d" % self.idmodele if self.idmodele else "Nouveau modèle de prestation"


class TarifLigne(models.Model):
    idligne = models.AutoField(verbose_name="ID", db_column='IDligne', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE, blank=True, null=True)
    tarif = models.ForeignKey(Tarif, verbose_name="Tarif", on_delete=models.CASCADE, blank=True, null=True)
    choix_methode = [(dict_methode["code"], dict_methode["label"]) for dict_methode in LISTE_METHODES_TARIFS]
    code = models.CharField(verbose_name="Méthode", max_length=200, choices=choix_methode, default="montant_unique", blank=True, null=True)
    num_ligne = models.IntegerField(verbose_name="Numéro de la ligne", blank=True, null=True)
    tranche = models.CharField(verbose_name="Nom de la tranche", max_length=50, blank=True, null=True)
    qf_min = models.DecimalField(verbose_name="QF min", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    qf_max = models.DecimalField(verbose_name="QF max", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_unique = models.DecimalField(verbose_name="Montant unique", max_digits=10, decimal_places=3, default=0.0, blank=True, null=True)
    montant_enfant_1 = models.DecimalField(verbose_name="Montant enfant 1", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_enfant_2 = models.DecimalField(verbose_name="Montant enfant 2", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_enfant_3 = models.DecimalField(verbose_name="Montant enfant 3", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_enfant_4 = models.DecimalField(verbose_name="Montant enfant 4", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_enfant_5 = models.DecimalField(verbose_name="Montant enfant 5", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_enfant_6 = models.DecimalField(verbose_name="Montant enfant 6", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    nbre_enfants = models.IntegerField(verbose_name="Nombre d'enfants pour le calcul par taux d'effort", blank=True, null=True)
    coefficient = models.DecimalField(verbose_name="Coefficient", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_min = models.DecimalField(verbose_name="Montant min", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    montant_max = models.DecimalField(verbose_name="Montant max", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    heure_debut_min = models.TimeField(verbose_name="Heure début min", blank=True, null=True)
    heure_debut_max = models.TimeField(verbose_name="Heure début min", blank=True, null=True)
    heure_fin_min = models.TimeField(verbose_name="Heure fin min", blank=True, null=True)
    heure_fin_max = models.TimeField(verbose_name="Heure fin max", blank=True, null=True)
    duree_min = models.TimeField(verbose_name="Durée min", blank=True, null=True)
    duree_max = models.TimeField(verbose_name="Durée max", blank=True, null=True)
    date = models.DateField(verbose_name="Date conditionnelle", blank=True, null=True)
    label = models.CharField(verbose_name="Label personnalisé", max_length=300, blank=True, null=True)
    temps_facture = models.TimeField(verbose_name="Temps facturé", blank=True, null=True)
    unite_horaire = models.TimeField(verbose_name="Unité horaire", blank=True, null=True)
    duree_seuil = models.TimeField(verbose_name="Durée seuil", blank=True, null=True)
    duree_plafond = models.TimeField(verbose_name="Durée plafond", blank=True, null=True)
    taux = models.DecimalField(verbose_name="Taux d'effort", max_digits=10, decimal_places=6, default=0.0, blank=True, null=True)
    ajustement = models.DecimalField(verbose_name="Ajustement", max_digits=10, decimal_places=4, default=0.0, blank=True, null=True)
    montant_questionnaire = models.CharField(verbose_name="Montant questionnaire", max_length=100, blank=True, null=True)
    revenu_min = models.DecimalField(verbose_name="Montant revenu min", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    revenu_max = models.DecimalField(verbose_name="Montant revenu max", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    duree_arrondi = models.TimeField(verbose_name="Durée arrondi", blank=True, null=True)
    # modele_prestation = models.ForeignKey(ModelePrestation, verbose_name="Modèle de prestation", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'tarifs_lignes'
        verbose_name = "ligne de tarif"
        verbose_name_plural = "lignes de tarif"

    def __str__(self):
        return "Ligne tarifaire ID%d - Tarif %s" % ( self.idligne, self.tarif.nom_tarif)


class CombiTarif(models.Model):
    idcombi_tarif = models.AutoField(verbose_name="ID", db_column='IDcombi_tarif', primary_key=True)
    tarif = models.ForeignKey(Tarif, verbose_name="Tarif", on_delete=models.CASCADE)
    type = models.CharField(verbose_name="Type", max_length=100, blank=True, null=True)
    date = models.DateField(verbose_name="Date", blank=True, null=True)
    quantite_max = models.IntegerField(verbose_name="Quantité maximale", blank=True, null=True)
    groupe = models.ForeignKey(Groupe, verbose_name="Groupe", on_delete=models.CASCADE, blank=True, null=True)
    unites = models.ManyToManyField(Unite, related_name="combi_tarif_unites")

    class Meta:
        db_table = 'combi_tarifs'
        verbose_name = "combinaison de tarif"
        verbose_name_plural = "combinaisons de tarif"

    def __str__(self):
        return "CombiTarif %d" % self.idcombi_tarif if self.idcombi_tarif else "Nouvelle combinaison"



class Ouverture(models.Model):
    idouverture = models.AutoField(verbose_name="ID", db_column='IDouverture', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    unite = models.ForeignKey(Unite, verbose_name="Unité de consommation", on_delete=models.CASCADE)
    groupe = models.ForeignKey(Groupe, verbose_name="Groupe", on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Date")

    class Meta:
        db_table = 'ouvertures'
        verbose_name = "ouverture"
        verbose_name_plural = "ouvertures"

    def __str__(self):
        return "Ouverture ID%d" % self.idouverture


class Remplissage(models.Model):
    idremplissage = models.AutoField(verbose_name="ID", db_column='IDremplissage', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    unite_remplissage = models.ForeignKey(UniteRemplissage, verbose_name="Unité de remplissage", on_delete=models.CASCADE)
    groupe = models.ForeignKey(Groupe, verbose_name="Groupe", on_delete=models.CASCADE, blank=True, null=True)
    date = models.DateField(verbose_name="Date")
    places = models.IntegerField(verbose_name="Nombre de places", blank=True, null=True)

    class Meta:
        db_table = 'remplissage'
        verbose_name = "remplissage"
        verbose_name_plural = "remplissages"

    def __str__(self):
        return "Remplissage ID%d" % self.idremplissage if self.idremplissage else "Nouveau"



class Individu(models.Model):
    idindividu = models.AutoField(verbose_name="ID", db_column='IDindividu', primary_key=True)
    civilite = models.IntegerField(verbose_name=_("Civilité"), db_column='IDcivilite', choices=data_civilites.GetListeCivilitesForModels(), default=1)
    nom = models.CharField(verbose_name=_("Nom"), max_length=200)
    nom_jfille = models.CharField(verbose_name=_("Nom de naissance"), max_length=200, blank=True, null=True)
    prenom = models.CharField(verbose_name=_("Prénom"), max_length=200, blank=True, null=True)
    idnationalite = models.IntegerField(verbose_name=_("Nationalité"), db_column='IDnationalite', blank=True, null=True)
    date_naiss = encrypt(models.DateField(verbose_name=_("Date de naissance"), blank=True, null=True))
    idpays_naiss = models.IntegerField(verbose_name=_("Pays de naissance"), db_column='IDpays_naiss', blank=True, null=True)
    cp_naiss = encrypt(models.CharField(verbose_name=_("Code postal"), max_length=50, blank=True, null=True))
    ville_naiss = encrypt(models.CharField(verbose_name=_("Ville"), max_length=200, blank=True, null=True))
    deces = models.BooleanField(verbose_name=_("Individu décédé"), default=False)
    annee_deces = models.IntegerField(verbose_name=_("Année de décès"), blank=True, null=True)
    adresse_auto = models.IntegerField(verbose_name=_("Adresse rattachée"), blank=True, null=True)
    rue_resid = encrypt(models.CharField(verbose_name=_("Rue"), max_length=200, blank=True, null=True))
    cp_resid = encrypt(models.CharField(verbose_name=_("Code postal"), max_length=50, blank=True, null=True))
    ville_resid = encrypt(models.CharField(verbose_name=_("Ville"), max_length=200, blank=True, null=True))
    secteur = models.ForeignKey(Secteur, verbose_name=_("Secteur"), on_delete=models.PROTECT, blank=True, null=True)
    categorie_travail = models.ForeignKey(CategorieTravail, verbose_name=_("Catégorie socio-professionnelle"), on_delete=models.PROTECT, blank=True, null=True)
    profession = encrypt(models.CharField(verbose_name=_("Profession"), max_length=200, blank=True, null=True))
    employeur = encrypt(models.CharField(verbose_name=_("Employeur"), max_length=200, blank=True, null=True))
    travail_tel = encrypt(models.CharField(verbose_name=_("Téléphone pro."), max_length=100, blank=True, null=True))
    travail_fax = encrypt(models.CharField(verbose_name=_("Fax pro."), max_length=100, blank=True, null=True))
    travail_mail = encrypt(models.EmailField(verbose_name=_("Email pro."), max_length=300, blank=True, null=True))
    tel_domicile = encrypt(models.CharField(verbose_name=_("Tél domicile"), max_length=100, blank=True, null=True))
    tel_mobile = encrypt(models.CharField(verbose_name=_("Tél portable"), max_length=100, blank=True, null=True))
    tel_fax = encrypt(models.CharField(verbose_name=_("Fax personnel"), max_length=100, blank=True, null=True))
    mail = encrypt(models.EmailField(verbose_name=_("Email personnel"), max_length=300, blank=True, null=True))
    medecin = models.ForeignKey(Medecin, verbose_name=_("Médecin"), on_delete=models.PROTECT, blank=True, null=True)
    memo = models.TextField(verbose_name=_("Mémo"), blank=True, null=True)
    type_sieste = models.ForeignKey(TypeSieste, verbose_name=_("Sieste"), on_delete=models.PROTECT, blank=True, null=True)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    travail_tel_sms = models.BooleanField(verbose_name="Autoriser l'envoi de SMS vers le téléphone pro.", default=False)
    tel_domicile_sms = models.BooleanField(verbose_name="Autoriser l'envoi de SMS vers le téléphone du domicile", default=False)
    tel_mobile_sms = models.BooleanField(verbose_name="Autoriser l'envoi de SMS vers le téléphone portable", default=False)
    etat = models.CharField(verbose_name="Etat", max_length=50, blank=True, null=True)
    photo = models.ImageField(verbose_name=_("Photo"), upload_to=get_uuid_path, blank=True, null=True)
    listes_diffusion = models.ManyToManyField(ListeDiffusion, blank=True, related_name="individu_listes_diffusion")
    regimes_alimentaires = models.ManyToManyField(RegimeAlimentaire, verbose_name=_("Régimes alimentaires"), related_name="individu_regimes_alimentaires", blank=True)
    maladies = models.ManyToManyField(TypeMaladie, verbose_name=_("Maladies contractées"), related_name="individu_maladies", blank=True)
    situation_familiale_choix = [(1, "Célibataires"), (2, "Mariés"), (3, "Divorcés"), (4, "Veuf(ve)"), (5, "En concubinage"), (6, "Séparés"), (7, "Pacsés"), (8, "En union libre"), (9, "Autre")]
    situation_familiale = models.IntegerField(verbose_name=_("Situation des parents"), choices=situation_familiale_choix, blank=True, null=True)
    type_garde_choix = [(1, "Mère"), (2, "Père"), (3, "Garde alternée"), (4, "Autre personne")]
    type_garde = models.IntegerField(verbose_name=_("Type de garde"), choices=type_garde_choix, blank=True, null=True)
    info_garde = models.TextField(verbose_name=_("Information sur la garde"), blank=True, null=True)

    class Meta:
        db_table = 'individus'
        verbose_name = "individu"
        verbose_name_plural = "individus"

    def __str__(self):
        return self.Get_nom()

    def Get_abrege_civilite(self):
        return data_civilites.Get_abrege(self)

    def Get_nom(self, avec_civilite=False):
        texte = ""
        if avec_civilite:
            texte += data_civilites.Get_abrege(self)
        texte = self.nom
        if self.prenom:
            texte += " " + self.prenom
        return texte

    def Get_age(self, today=None):
        if self.date_naiss:
            if not today: today = datetime.date.today()
            return today.year - self.date_naiss.year - ((today.month, today.day) < (self.date_naiss.month, self.date_naiss.day))
        else:
            return None

    def Get_adresse(self):
        individu = self
        if self.adresse_auto:
            try:
                individu = Individu.objects.get(pk=self.adresse_auto)
            except:
                pass
        adresse_complete = " ".join([x for x in (individu.rue_resid, individu.cp_resid, individu.ville_resid) if x])
        cp_ville = " ".join([x for x in (individu.cp_resid, individu.ville_resid) if x])
        mail = individu.mail if individu.mail else None
        return {"rue": individu.rue_resid, "cp": individu.cp_resid, "ville": individu.ville_resid, "cp_ville": cp_ville,
                "adresse_complete": adresse_complete, "secteur": individu.secteur, "mail": mail}

    def Get_rue_resid(self):
        return self.rue_resid.replace("\n", "<br/>") if self.rue_resid else None

    def Get_ville_resid(self):
        return self.ville_resid

    def Get_adresse_complete(self):
        return " ".join([x for x in (self.rue_resid, self.cp_resid, self.ville_resid) if x])

    def Get_photo(self, forTemplate=True):
        if self.photo:
            return self.photo.url
        dict_civilite = data_civilites.GetCiviliteForIndividu(self)
        if forTemplate:
            return static("images/" + dict_civilite["image"])
        else:
            return settings.STATIC_ROOT + "/images/" + dict_civilite["image"]

    def Get_sexe(self):
        dict_civilite = data_civilites.GetCiviliteForIndividu(self)
        return dict_civilite["sexe"]

    def Maj_infos(self):
        if self.adresse_auto:
            dict_adresse = self.Get_adresse()
            self.rue_resid = dict_adresse["rue"]
            self.cp_resid = dict_adresse["cp"]
            self.ville_resid = dict_adresse["ville"]
            self.secteur = dict_adresse["secteur"]
            self.save()


class Scolarite(models.Model):
    idscolarite = models.AutoField(verbose_name="ID", db_column='IDscolarite', primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.CASCADE)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    ecole = models.ForeignKey(Ecole, verbose_name="Ecole", on_delete=models.PROTECT)
    classe = models.ForeignKey(Classe, verbose_name="Classe", on_delete=models.PROTECT, blank=True, null=True)
    niveau = models.ForeignKey(NiveauScolaire, verbose_name="Niveau", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'scolarite'
        verbose_name = "étape de scolarité"
        verbose_name_plural = "étapes de scolarité"

    def __str__(self):
        return "Etape de scolarité du %s au %s" % (self.date_debut.strftime('%d/%m/%Y'), self.date_fin.strftime('%d/%m/%Y'))


class CategorieCompteInternet(models.Model):
    idcategorie = models.AutoField(verbose_name="ID", db_column='IDcategorie', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = 'categories_compte_internet'
        verbose_name = "catégorie de compte internet"
        verbose_name_plural = "catégories de compte internet"

    def __str__(self):
        return self.nom


class Famille(models.Model):
    idfamille = models.AutoField(verbose_name="ID", db_column='IDfamille', primary_key=True)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    # idcompte_payeur = models.IntegerField(db_column='IDcompte_payeur', blank=True, null=True)  # Field name made lowercase.
    caisse = models.ForeignKey(Caisse, verbose_name="Caisse", blank=True, null=True, on_delete=models.PROTECT)
    num_allocataire = encrypt(models.CharField(verbose_name="Numéro d'allocataire", max_length=100, blank=True, null=True))
    allocataire = models.ForeignKey(Individu, verbose_name="Titulaire", on_delete=models.CASCADE, blank=True, null=True)
    autorisation_cafpro = models.BooleanField(verbose_name="Autorisation accès CAF-CDAP", default=False)
    internet_actif = models.BooleanField(verbose_name="Compte internet activé", default=True)
    internet_identifiant = encrypt(models.CharField(verbose_name="Identifiant", max_length=200, blank=True, null=True))
    internet_mdp = encrypt(models.CharField(verbose_name="Mot de passe", max_length=200, blank=True, null=True))
    internet_secquest = models.CharField(verbose_name="Question", max_length=200, blank=True, null=True)
    internet_categorie = models.ForeignKey(CategorieCompteInternet, verbose_name="Catégorie", related_name="internet_categorie", on_delete=models.PROTECT, blank=True, null=True)
    internet_reservations = models.BooleanField(verbose_name="Autoriser les réservations sur le portail", default=True)
    memo = models.TextField(verbose_name="Mémo", blank=True, null=True)
    email_factures = models.BooleanField(verbose_name="Activation de l'envoi des factures par Email", default=False)
    email_factures_adresses = models.CharField(verbose_name="Adresses pour l'envoi des factures par Email", max_length=400, blank=True, null=True)
    email_recus = models.BooleanField(verbose_name="Activation de l'envoi des reçus par Email", default=False)
    email_recus_adresses = models.CharField(verbose_name="Adresses pour l'envoi des reçus par Email", max_length=400, blank=True, null=True)
    email_depots = models.BooleanField(verbose_name="Activation de l'envoi des avis d'encaissement par Email", default=False)
    email_depots_adresses = models.CharField(verbose_name="Adresses pour l'envoi des avis d'encaissement par Email", max_length=400, blank=True, null=True)
    code_compta = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    titulaire_helios = models.ForeignKey(Individu, verbose_name="Titulaire Hélios", related_name="titulaire_helios", on_delete=models.SET_NULL, blank=True, null=True)
    tiers_solidaire = models.ForeignKey(Individu, verbose_name="Tiers solidaire", related_name="tiers_solidaire", on_delete=models.SET_NULL, blank=True, null=True)
    idtiers_helios = models.CharField(verbose_name="Identifiant national", max_length=300, blank=True, null=True, help_text="Saisissez l'identifiant national (SIRET ou SIREN ou FINESS ou NIR)")
    natidtiers_helios = models.IntegerField(verbose_name="Type d'identifiant national", blank=True, null=True, choices=LISTE_TYPES_ID_TIERS, default=9999, help_text="Sélectionnez le type d'identifiant national du tiers pour Hélios (Trésor Public)")
    reftiers_helios = models.CharField(verbose_name="Référence locale", max_length=200, blank=True, null=True, help_text="Saisissez la référence locale du tiers")
    cattiers_helios = models.IntegerField(verbose_name="Catégorie de tiers", blank=True, null=True, choices=LISTE_CATEGORIES_TIERS, default=1, help_text="Sélectionnez la catégorie de tiers pour Hélios (Trésor Public)")
    natjur_helios = models.IntegerField(verbose_name="Nature juridique", blank=True, null=True, choices=LISTE_NATURES_JURIDIQUES, default=1, help_text="Sélectionnez la nature juridique du tiers pour Hélios (Trésor Public)")
    # autre_adresse_facturation = models.CharField(blank=True, null=True)
    etat = models.CharField(verbose_name="Etat", max_length=100, blank=True, null=True)
    nom = models.CharField(verbose_name="Nom", max_length=300, blank=True, null=True)
    rue_resid = encrypt(models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True))
    cp_resid = encrypt(models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True))
    ville_resid = encrypt(models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True))
    secteur = models.ForeignKey(Secteur, verbose_name="Secteur", on_delete=models.PROTECT, blank=True, null=True)
    mail = encrypt(models.EmailField(verbose_name="Email favori", max_length=300, blank=True, null=True))
    mobile = encrypt(models.CharField(verbose_name="Portable favori", max_length=100, blank=True, null=True))
    utilisateur = models.OneToOneField(Utilisateur, on_delete=models.CASCADE, null=True)
    certification_date = models.DateTimeField(verbose_name="Date de certification", blank=True, null=True)
    facturation_nom = models.CharField(verbose_name="Nom", max_length=300, blank=True, null=True)
    facturation_rue_resid = encrypt(models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True))
    facturation_cp_resid = encrypt(models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True))
    facturation_ville_resid = encrypt(models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True))
    email_blocage = models.BooleanField(verbose_name="La famille ne souhaite pas recevoir de mails groupés", default=False, help_text="L'éditeur d'emails groupés du menu Outils ne proposera pas cette famille dans les destinataires.")
    mobile_blocage = models.BooleanField(verbose_name="La famille ne souhaite pas recevoir de SMS groupés", default=False, help_text="L'éditeur de SMS groupés du menu Outils ne proposera pas cette famille dans les destinataires.")
    individus_masques = models.ManyToManyField(Individu, verbose_name="Individus masqués", related_name="individus_masques", blank=True)

    class Meta:
        db_table = 'familles'
        verbose_name = "famille"
        verbose_name_plural = "familles"

    def __str__(self):
        return self.nom if self.nom else "Famille ID%s" % self.pk

    def Maj_infos(self, maj_adresse=True, maj_mail=True, maj_mobile=True, maj_titulaire_helios=True, maj_tiers_solidaire=True, maj_code_compta=True):
        """ MAJ du nom des titulaires et de l'adresse de la famille """
        # MAJ Adresse de la famille
        if maj_adresse:
            dict_infos = self.Get_infos()
            self.nom = dict_infos["nom"]
            self.rue_resid = dict_infos.get("rue", None)
            self.cp_resid = dict_infos.get("cp", None)
            self.ville_resid = dict_infos.get("ville", None)
            self.secteur = dict_infos.get("secteur", None)

        # Recherche des titulaires
        rattachements = Rattachement.objects.prefetch_related('individu').filter(famille=self, categorie=1, titulaire=True).order_by("pk")

        # Mail favori
        if maj_mail:
            if self.mail:
                # recherche si l'adresse est toujours celle d'un titulaire de la famille
                found = False
                for rattachement in rattachements:
                    if rattachement.individu.mail == self.mail:
                        found = True
                if not found:
                    self.mail = None
            if not self.mail:
                # Recherche une adresse mail valide parmi les titulaires de la famille
                for rattachement in rattachements:
                    if rattachement.individu.mail:
                        self.mail = rattachement.individu.mail
                        break

        # Mobile favori
        if maj_mobile:
            if self.mobile:
                # recherche si le mobile est toujours celui d'un titulaire de la famille
                found = False
                for rattachement in rattachements:
                    if rattachement.individu.tel_mobile == self.mobile:
                        found = True
                if not found:
                    self.mobile = None
            if not self.mobile:
                # Recherche un numéro de mobile valide parmi les titulaires de la famille
                for rattachement in rattachements:
                    if rattachement.individu.tel_mobile:
                        self.mobile = rattachement.individu.tel_mobile
                        break

        # Titulaire Hélios
        if maj_titulaire_helios:
            if self.titulaire_helios:
                # recherche si le titulaire est toujours dans la famille
                found = False
                for rattachement in rattachements:
                    if rattachement.individu == self.titulaire_helios:
                        found = True
                if not found:
                    self.titulaire_helios = None
            if not self.titulaire_helios:
                # Recherche un individu valide parmi les titulaires de la famille
                if rattachements:
                    self.titulaire_helios = rattachements.first().individu

        if maj_tiers_solidaire:
            if self.tiers_solidaire:
                # recherche si le titulaire est toujours dans la famille
                found = False
                for rattachement in rattachements:
                    if rattachement.individu == self.tiers_solidaire:
                        found = True
                if not found:
                    self.tiers_solidaire = None
            if not self.tiers_solidaire:
                # Recherche un individu valide parmi les titulaires de la famille
                if rattachements:
                    for rattachement in rattachements:
                        if rattachement.individu != self.titulaire_helios:
                            self.tiers_solidaire = rattachement.individu
                            break

        # Code comptable
        if maj_code_compta:
            if not self.code_compta and rattachements:
                titulaire = rattachements.first()
                nom = utils_texte.Supprimer_accents(titulaire.individu.nom.upper())
                prenom = utils_texte.Supprimer_accents(titulaire.individu.prenom.upper()) if titulaire.individu.prenom else ""
                self.code_compta = ("%d%s_%s" % (self.idfamille, nom, prenom))[:15]

        self.save()

    def Get_rue_resid(self):
        return self.rue_resid.replace("\n", "<br/>") if self.rue_resid else None

    def Get_infos(self, avec_civilite=False):
        """ Renvoie le nom des titulaires """
        rattachements = Rattachement.objects.prefetch_related('individu').filter(famille=self, categorie=1, titulaire=True).order_by("individu__civilite")

        # Cherche si les noms de famille sont identiques
        dict_noms = {}
        for rattachement in rattachements:
            if rattachement.individu.nom not in dict_noms:
                dict_noms[rattachement.individu.nom] = []
            dict_noms[rattachement.individu.nom].append(rattachement.individu.prenom or "")

        nom_titulaires = ""
        if len(dict_noms) == 1:
            for nom, liste_prenoms in dict_noms.items():
                nom_titulaires = nom + " " + utils_texte.Convert_liste_to_texte_virgules(liste_prenoms)
        else:
            liste_noms = [rattachement.individu.Get_nom(avec_civilite=avec_civilite) for rattachement in rattachements]
            nom_titulaires = utils_texte.Convert_liste_to_texte_virgules(liste_noms)

        resultats = {"nom": nom_titulaires}
        if rattachements:
            resultats.update(rattachements.first().individu.Get_adresse())
        return resultats


class Inscription(models.Model):
    idinscription = models.AutoField(verbose_name="ID", db_column='IDinscription', primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.PROTECT)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.PROTECT)
    groupe = models.ForeignKey(Groupe, verbose_name="Groupe", on_delete=models.PROTECT)
    categorie_tarif = models.ForeignKey(CategorieTarif, verbose_name="Catégorie de tarif", on_delete=models.PROTECT)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    statut_choix = [("ok", "Inscription validée"), ("attente", "Inscription en attente"), ("refus", "Inscription refusée")]
    statut = models.CharField(verbose_name="Statut", max_length=100, choices=statut_choix, default="ok")
    internet_reservations = models.BooleanField(verbose_name="Autoriser les réservations sur le portail", default=True)

    class Meta:
        db_table = 'inscriptions'
        verbose_name = "inscription"
        verbose_name_plural = "inscriptions"

    def __str__(self):
        try:
            return "Inscription de %s à l'activité %s" % (self.individu, self.activite)
        except:
            return "Inscription ID%d" % self.idinscription

    def Is_date_in_inscription(self, date=None):
        """ Est-ce que la date est comprise dans la période d'inscription ? """
        if self.date_fin:
            return self.date_debut <= date <= self.date_fin
        else:
            return self.date_debut <= date

    def Is_inscription_in_periode(self, date_min=None, date_max=None):
        if self.date_fin:
            return self.date_debut <= date_max and self.date_fin >= date_min
        else:
            return self.date_debut <= date_max


class Information(models.Model):
    idinformation = models.AutoField(verbose_name="ID", db_column='IDinformation', primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.CASCADE)
    categorie = models.ForeignKey(CategorieInformation, verbose_name=_("Catégorie"), on_delete=models.PROTECT)
    intitule = encrypt(models.CharField(verbose_name=_("Intitulé"), max_length=200))
    date_debut = models.DateField(verbose_name=_("Date de début"), blank=True, null=True)
    date_fin = models.DateField(verbose_name=_("Date de fin"), blank=True, null=True)
    description = encrypt(models.TextField(verbose_name=_("Description"), blank=True, null=True))
    traitement_medical = models.BooleanField(verbose_name="Traitement médical", default=False)
    description_traitement = encrypt(models.TextField(verbose_name="Traitement", blank=True, null=True))
    date_debut_traitement = models.DateField(verbose_name="Date de début du traitement", blank=True, null=True)
    date_fin_traitement = models.DateField(verbose_name="Date de fin du traitement", blank=True, null=True)
    eviction = models.BooleanField(verbose_name="Eviction", default=False)
    date_debut_eviction = models.DateField(verbose_name="Date de début de l'éviction", blank=True, null=True)
    date_fin_eviction = models.DateField(verbose_name="Date de fin de l'éviction", blank=True, null=True)
    diffusion_listing_enfants = models.BooleanField(verbose_name="Afficher sur la liste des informations personnelles", default=False)
    diffusion_listing_conso = models.BooleanField(verbose_name="Afficher sur la liste des consommations", default=False)
    diffusion_listing_repas = models.BooleanField(verbose_name="Afficher sur la commande des repas", default=False)
    document = models.FileField(verbose_name=_("Document"), storage=get_storage("probleme"), upload_to=get_uuid_path, blank=True, null=True, help_text="Vous pouvez ajouter un document.")

    class Meta:
        db_table = 'informations'
        verbose_name = "information"
        verbose_name_plural = "informations"

    def __str__(self):
        return self.intitule

    def get_upload_path(self):
        return str(self.individu_id)


class Vaccin(models.Model):
    idvaccin = models.AutoField(verbose_name="ID", db_column='IDvaccin', primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.CASCADE)
    type_vaccin = models.ForeignKey(TypeVaccin, verbose_name=_("Type de vaccin"), on_delete=models.PROTECT)
    date = models.DateField(verbose_name=_("Date de vaccination"))

    class Meta:
        db_table = 'vaccins'
        verbose_name = "vaccin"
        verbose_name_plural = "vaccins"

    def __str__(self):
        return "Vaccin %s du %s" % (self.type_vaccin, self.date.strftime('%d/%m/%Y'))


class Note(models.Model):
    idnote = models.AutoField(verbose_name="ID", db_column='IDnote', primary_key=True)
    type_choix = [("INSTANTANE", "Instantané"), ("PROGRAMME", "Programmé")]
    type = models.CharField(verbose_name="Priorité", max_length=100, choices=type_choix, default="INSTANTANE")
    categorie = models.ForeignKey(NoteCategorie, verbose_name="Catégorie", on_delete=models.PROTECT, blank=True, null=True, help_text="Vous pouvez sélectionner une catégorie de note (optionnel).")
    date_saisie = models.DateTimeField(verbose_name="Date de saisie", auto_now_add=True)
    date_parution = models.DateField(verbose_name="Date de parution", help_text="Cette option permet de différer la parution de la note. Par défaut la date du jour.")
    priorite_choix = [("NORMALE", "Normale"), ("HAUTE", "Haute")]
    priorite = models.CharField(verbose_name="Priorité", max_length=100, choices=priorite_choix, default="NORMALE")
    afficher_accueil = models.BooleanField(verbose_name="Afficher sur la page d'accueil", default=False)
    afficher_liste = models.BooleanField(verbose_name="Afficher sur la liste des consommations", default=False)
    rappel = models.BooleanField(verbose_name="Rappel à l'ouverture de Noethys", default=False)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE, blank=True, null=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.CASCADE, blank=True, null=True)
    collaborateur = models.ForeignKey("Collaborateur", verbose_name="Collaborateur", blank=True, null=True, on_delete=models.CASCADE)
    texte = models.TextField(verbose_name="Texte", help_text="Saisissez ici le texte de la note.")
    afficher_facture = models.BooleanField(verbose_name="Afficher sur la facture", default=False)
    rappel_famille = models.BooleanField(verbose_name="Rappel à l'ouverture de la fiche famille", default=False)
    afficher_commande = models.BooleanField(verbose_name="Afficher sur la commande des repas", default=False)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.CASCADE)
    structure = models.ForeignKey(Structure, verbose_name="Structure", blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'notes'
        verbose_name = "note"
        verbose_name_plural = "notes"

    def __str__(self):
        return "Note du %s" % self.date_saisie.strftime('%d/%m/%Y')


class Rattachement(models.Model):
    idrattachement = models.AutoField(verbose_name="ID", db_column='IDrattachement', primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.CASCADE, blank=True, null=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE, blank=True, null=True)
    categorie = models.IntegerField(db_column='Catégorie', choices=CATEGORIES_RATTACHEMENT, default=1)
    titulaire = models.BooleanField(verbose_name="Titulaire du dossier", default=False)
    certification_date = models.DateTimeField(verbose_name="Date de certification", blank=True, null=True)

    class Meta:
        db_table = 'rattachements'
        verbose_name = "rattachement"
        verbose_name_plural = "rattachements"

    def __str__(self):
        return "Rattachement ID%d" % self.idrattachement

    def Get_profil(self):
        if self.categorie == 1: return "Responsable" + " titulaire" if self.titulaire else ""
        if self.categorie == 2: return "Enfant"
        if self.categorie == 3: return "Contact"
        return ""


class Piece(models.Model):
    idpiece = models.AutoField(verbose_name="ID", db_column='IDpiece', primary_key=True)
    type_piece = models.ForeignKey(TypePiece, verbose_name="Type de pièce", on_delete=models.PROTECT, blank=True, null=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.CASCADE, blank=True, null=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début", blank=True, null=True)
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    document = models.FileField(verbose_name="Document", storage=get_storage("piece"), upload_to=get_uuid_path, blank=True, null=True)
    titre = models.CharField(verbose_name="Titre", max_length=200, blank=True, null=True)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    auteur = models.ForeignKey(Utilisateur, verbose_name="Auteur", blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        db_table = 'pieces'
        verbose_name = "pièce"
        verbose_name_plural = "pièces"

    def __str__(self):
        return self.Get_nom()

    def Get_nom(self):
        if not self.type_piece:
            return self.titre
        if self.type_piece.public == "individu":
            prenom = self.individu.prenom or self.individu.nom
            return self.type_piece.nom + " de " + prenom
        else:
            return self.type_piece.nom


class Location(models.Model):
    idlocation = models.AutoField(verbose_name="ID", db_column="IDlocation", primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    produit = models.ForeignKey(Produit, verbose_name="Produit", on_delete=models.PROTECT)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    date_saisie = models.DateField(verbose_name="Date de saisie", auto_now_add=True)
    date_debut = models.DateTimeField(verbose_name="Début", blank=True, null=True)
    date_fin = models.DateTimeField(verbose_name="Fin", blank=True, null=True)
    quantite = models.IntegerField(verbose_name="Quantité", default=1)
    serie = models.CharField(verbose_name="Série", max_length=200, blank=True, null=True)

    class Meta:
        db_table = "locations"
        verbose_name = "location"
        verbose_name_plural = "locations"

    def __str__(self):
        return "Location ID%d" % self.idlocation if self.idlocation else "Nouvelle location"


class LotFactures(models.Model):
    idlot = models.AutoField(verbose_name="ID", db_column='IDlot', primary_key=True)
    nom = models.CharField(verbose_name="Nom du lot", max_length=200)

    class Meta:
        db_table = 'lots_factures'
        verbose_name = "lot de factures"
        verbose_name_plural = "lots de factures"

    def __str__(self):
        return self.nom if self.nom else "Nouveau lot de factures"


class PrefixeFacture(models.Model):
    idprefixe = models.AutoField(verbose_name="ID", db_column='IDprefixe', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    prefixe = models.CharField(verbose_name="Préfixe", max_length=200)

    class Meta:
        db_table = 'factures_prefixes'
        verbose_name = "préfixe de factures"
        verbose_name_plural = "préfixes de factures"

    def __str__(self):
        return self.nom if self.nom else "Nouveau préfixe de factures"


class MessageFacture(models.Model):
    idmessage = models.AutoField(verbose_name="ID", db_column='IDmessage', primary_key=True)
    titre = models.CharField(verbose_name="Titre", max_length=300)
    texte = models.TextField(verbose_name="Texte")

    class Meta:
        db_table = 'factures_messages'
        verbose_name = "message de factures"
        verbose_name_plural = "messages de factures"

    def __str__(self):
        return self.titre if self.titre else "Nouveau message de factures"


class Facture(models.Model):
    idfacture = models.AutoField(verbose_name="ID", db_column='IDfacture', primary_key=True)
    numero = models.BigIntegerField(verbose_name="Numéro")
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT, blank=True, null=True)
    date_edition = models.DateField(verbose_name="Date")
    date_echeance = models.DateField(verbose_name="Date d'échéance", blank=True, null=True)
    activites = models.CharField(verbose_name="Activités associées", max_length=200, blank=True, null=True)
    individus = models.CharField(verbose_name="Individus associés", max_length=200, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Début")
    date_fin = models.DateField(verbose_name="Fin")
    total = models.DecimalField(verbose_name="Total", max_digits=10, decimal_places=2, default=0.0)
    regle = models.DecimalField(verbose_name="Réglé", max_digits=10, decimal_places=2, default=0.0)
    solde = models.DecimalField(verbose_name="Solde", max_digits=10, decimal_places=2, default=0.0)
    solde_actuel = models.DecimalField(verbose_name="Solde actuel", max_digits=10, decimal_places=2, default=0.0)
    lot = models.ForeignKey(LotFactures, verbose_name="Lot de factures", on_delete=models.PROTECT, blank=True, null=True)
    prestations = models.CharField(verbose_name="Types de prestations", max_length=200, blank=True, null=True)
    etat = models.CharField(verbose_name="Etat de la facture", max_length=100, blank=True, null=True)
    prefixe = models.ForeignKey(PrefixeFacture, verbose_name="Préfixe", on_delete=models.PROTECT, blank=True, null=True)
    regie = models.ForeignKey(FactureRegie, verbose_name="Régie", on_delete=models.PROTECT, blank=True, null=True)
    date_limite_paiement = models.DateField(verbose_name="Date limite paiement en ligne", blank=True, null=True)

    class Meta:
        db_table = 'factures'
        verbose_name = "facture"
        verbose_name_plural = "factures"

    def __str__(self):
        return "Facture ID%d" % self.idfacture

    def Maj_solde_actuel(self):
        if self.etat == "annulation":
            return
        montant_regle = Ventilation.objects.filter(prestation__facture=self.idfacture).aggregate(Sum('montant'))["montant__sum"]
        if not montant_regle:
            montant_regle = decimal.Decimal(0)
        solde_actuel = self.total - montant_regle
        if solde_actuel != self.solde_actuel:
            self.regle = montant_regle
            self.solde_actuel = solde_actuel
            self.save()

    def Get_regle_actuel(self):
        return self.total - self.solde_actuel


class Prestation(models.Model):
    idprestation = models.AutoField(verbose_name="ID", db_column='IDprestation', primary_key=True)
    date = models.DateField(verbose_name="Date")
    categorie_choix = [("cotisation", "Adhésion"), ("consommation", "Consommation"), ("location", "Location"), ("autre", "Autre")]
    categorie = models.CharField(verbose_name="Catégorie", max_length=100, choices=categorie_choix, default="autre")
    label = models.CharField(verbose_name="Label", max_length=200)
    montant_initial = models.DecimalField(verbose_name="Montant initial", max_digits=10, decimal_places=2, default=0.0)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.PROTECT, blank=True, null=True)
    tarif = models.ForeignKey(Tarif, verbose_name="Tarif", on_delete=models.PROTECT, blank=True, null=True)
    facture = models.ForeignKey(Facture, verbose_name="Facture", on_delete=models.SET_NULL, blank=True, null=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT, blank=True, null=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.PROTECT, blank=True, null=True)
    forfait = models.IntegerField(verbose_name="Type de forfait", blank=True, null=True)
    temps_facture = models.DurationField(verbose_name="Temps facturé", blank=True, null=True)
    categorie_tarif = models.ForeignKey(CategorieTarif, verbose_name="Catégorie de tarif", on_delete=models.PROTECT, blank=True, null=True)
    quantite = models.PositiveIntegerField(verbose_name="Quantité", default=1, validators=[MinValueValidator(1)])
    forfait_date_debut = models.DateField(verbose_name="Date de début du forfait", blank=True, null=True)
    forfait_date_fin = models.DateField(verbose_name="Date de fin du forfait", blank=True, null=True)
    # reglement_frais = models.IntegerField(blank=True, null=True)
    tva = models.DecimalField(verbose_name="Taux de TVA", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    code_compta = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    code_analytique = models.CharField(verbose_name="Code analytique", max_length=200, blank=True, null=True)
    # idcontrat = models.IntegerField(db_column='IDcontrat', blank=True, null=True)  # Field name made lowercase.
    date_valeur = models.DateField(verbose_name="Date de valeur", auto_now_add=True)
    # iddonnee = models.IntegerField(db_column='IDdonnee', blank=True, null=True)  # Field name made lowercase.
    code_produit_local = models.CharField(verbose_name="Code produit local", max_length=200, blank=True, null=True)
    tarif_ligne = models.ForeignKey(TarifLigne, verbose_name="Ligne de tarif", on_delete=models.SET_NULL, blank=True, null=True)
    location = models.ForeignKey(Location, verbose_name="Location", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'prestations'
        verbose_name = "prestation"
        verbose_name_plural = "prestations"

    def __str__(self):
        return "Prestation ID%d : %s" % (self.idprestation, self.label)




class Consommation(models.Model):
    idconso = models.AutoField(verbose_name="ID", db_column='IDconso', primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.PROTECT)
    inscription = models.ForeignKey(Inscription, verbose_name="Inscription", blank=True, null=True, on_delete=models.PROTECT)
    activite = models.ForeignKey(Activite, verbose_name="Activité", blank=True, null=True, on_delete=models.PROTECT)
    date = models.DateField(verbose_name="Date", blank=True, null=True)
    unite = models.ForeignKey(Unite, verbose_name="Unité de consommation", blank=True, null=True, on_delete=models.PROTECT)
    groupe = models.ForeignKey(Groupe, verbose_name="Groupe", blank=True, null=True, on_delete=models.PROTECT)
    heure_debut = models.TimeField(verbose_name="Heure de début", blank=True, null=True)
    heure_fin = models.TimeField(verbose_name="Heure de fin", blank=True, null=True)
    etat = models.CharField(verbose_name="Etat", max_length=100, choices=LISTE_ETATS_CONSO, blank=True, null=True)
    # verrouillage = models.IntegerField(blank=True, null=True)
    date_saisie = models.DateTimeField(verbose_name="Date de saisie", auto_now_add=True)
    # idutilisateur = models.IntegerField(db_column='IDutilisateur', blank=True, null=True)  # Field name made lowercase.
    categorie_tarif = models.ForeignKey(CategorieTarif, verbose_name="Catégorie de tarif", on_delete=models.PROTECT, blank=True, null=True)
    # idcompte_payeur = models.IntegerField(db_column='IDcompte_payeur', blank=True, null=True)  # Field name made lowercase.
    prestation = models.ForeignKey(Prestation, verbose_name="Prestation", on_delete=models.PROTECT, blank=True, null=True)
    forfait = models.IntegerField(verbose_name="Type de forfait", blank=True, null=True)
    quantite = models.IntegerField(verbose_name="Quantité", blank=True, null=True, default=1)
    # etiquettes = models.CharField(blank=True, null=True)
    evenement = models.ForeignKey(Evenement, verbose_name="Evénement", blank=True, null=True, on_delete=models.PROTECT)
    badgeage_debut = models.DateTimeField(verbose_name="Badgeage début", blank=True, null=True)
    badgeage_fin = models.DateTimeField(verbose_name="Badgeage fin", blank=True, null=True)

    class Meta:
        db_table = 'consommations'
        verbose_name = "consommation"
        verbose_name_plural = "consommations"

    def __str__(self):
        return "Consommation ID%d" % self.idconso if self.idconso else "Nouveau"


class DepotCotisations(models.Model):
    iddepot = models.AutoField(verbose_name="ID", db_column='IDdepot', primary_key=True)
    date = models.DateField(verbose_name="Date")
    nom = models.CharField(verbose_name="Nom", max_length=200)
    verrouillage = models.BooleanField(verbose_name="Verrouillage", default=False)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    quantite = models.IntegerField(verbose_name="Quantité", blank=True, null=True)

    class Meta:
        db_table = 'depots_cotisations'
        verbose_name = "dépôt d'adhésions"
        verbose_name_plural = "dépôts d'adhésions"

    def __str__(self):
        if self.nom and self.date:
            return "%s (%s)" % (self.nom, utils_dates.ConvertDateToFR(self.date))
        return self.nom if self.nom else "Nouveau dépôt"

    def Maj_quantite(self):
        self.quantite = Cotisation.objects.filter(depot_cotisation=self).count()
        self.save()


class Cotisation(models.Model):
    idcotisation = models.AutoField(verbose_name="ID", db_column='IDcotisation', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT, blank=True, null=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.PROTECT, blank=True, null=True)
    type_cotisation = models.ForeignKey(TypeCotisation, verbose_name="Type d'adhésion", on_delete=models.PROTECT)
    unite_cotisation = models.ForeignKey(UniteCotisation, verbose_name="Unité d'adhésion", on_delete=models.PROTECT)
    date_saisie = models.DateTimeField(verbose_name="Date de saisie", auto_now_add=True)
    # idutilisateur = models.IntegerField(db_column='IDutilisateur', blank=True, null=True)  # Field name made lowercase.
    date_creation_carte = models.DateField(verbose_name="Date de création", blank=True, null=True)
    numero = models.CharField(verbose_name="Numéro", max_length=100, blank=True, null=True)
    depot_cotisation = models.ForeignKey(DepotCotisations, verbose_name="Dépôt d'adhésions", on_delete=models.PROTECT, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    prestation = models.OneToOneField(Prestation, verbose_name="Prestation", on_delete=models.SET_NULL, blank=True, null=True)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    activites = models.ManyToManyField(Activite, verbose_name="Activités", blank=True)

    class Meta:
        db_table = 'cotisations'
        verbose_name = "adhésion"
        verbose_name_plural = "adhésions"

    def __str__(self):
        return "Adhésion ID%d" % self.idcotisation

    def delete(self, *args, **kwargs):
        # Avant la suppression
        if self.depot_cotisation:
            return "La suppression de '%s' est impossible car cette adhésion est déjà incluse dans un dépôt" % self
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Après la suppression
        if self.prestation:
            self.prestation.delete()


class Aide(models.Model):
    idaide = models.AutoField(verbose_name="ID", db_column='IDaide', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", blank=True, null=True, on_delete=models.PROTECT)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.PROTECT)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    caisse = models.ForeignKey(Caisse, verbose_name="Caisse", blank=True, null=True, on_delete=models.PROTECT)
    montant_max = models.DecimalField(verbose_name="Montant plafond", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)
    nbre_dates_max = models.IntegerField(verbose_name="Quantité plafond", blank=True, null=True)
    jours_scolaires = MultiSelectField(verbose_name="Jours sur les périodes scolaires", max_length=100, choices=JOURS_SEMAINE, blank=True, null=True)
    jours_vacances = MultiSelectField(verbose_name="Jours sur les périodes de vacances", max_length=100, choices=JOURS_SEMAINE, blank=True, null=True)
    individus = models.ManyToManyField(Individu, verbose_name="Bénéficiaires", blank=True)

    class Meta:
        db_table = 'aides'
        verbose_name = "aide"
        verbose_name_plural = "aides"

    def __str__(self):
        return self.nom


class CombiAide(models.Model):
    idcombi_aide = models.AutoField(verbose_name="ID", db_column='IDcombi_aide', primary_key=True)
    aide = models.ForeignKey(Aide, verbose_name="Aide", on_delete=models.CASCADE)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    unites = models.ManyToManyField(Unite)

    class Meta:
        db_table = 'combi_aides'
        verbose_name = "combinaison d'aide"
        verbose_name_plural = "combinaisons d'aide"

    def __str__(self):
        return "CombiAide ID%d" % self.idcombi_aide


class Quotient(models.Model):
    idquotient = models.AutoField(verbose_name="ID", db_column='IDquotient', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    quotient = encrypt(models.DecimalField(verbose_name="Quotient", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True))
    revenu = encrypt(models.DecimalField(verbose_name="Revenu", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True))
    observations = encrypt(models.TextField(verbose_name="Observations", blank=True, null=True))
    type_quotient = models.ForeignKey(TypeQuotient, verbose_name="Type de quotient", on_delete=models.PROTECT)
    document = models.FileField(verbose_name="Document", storage=get_storage("quotient"), upload_to=get_uuid_path, blank=True, null=True)

    class Meta:
        db_table = 'quotients'
        verbose_name = "quotient"
        verbose_name_plural = "quotients"

    def __str__(self):
        return "Quotient ID%d" % self.idquotient

    def get_upload_path(self):
        return str(self.famille_id)


class Deduction(models.Model):
    iddeduction = models.AutoField(verbose_name="ID", db_column='IDdeduction', primary_key=True)
    prestation = models.ForeignKey(Prestation, verbose_name="Prestation", on_delete=models.CASCADE)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    date = models.DateField(verbose_name="Date")
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    label = models.CharField(verbose_name="Label", max_length=200)
    aide = models.ForeignKey(Aide, verbose_name="Aide", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'deductions'
        verbose_name = "déduction"
        verbose_name_plural = "déductions"

    def __str__(self):
        return "Déduction ID%d" % self.iddeduction



class ModeleDocument(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column='IDmodele', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CHOIX_CATEGORIE_MODELE_DOCUMENT)
    # supprimable = models.BooleanField(verbose_name="Supprimable", default=True)
    largeur = models.IntegerField(verbose_name="Largeur")
    hauteur = models.IntegerField(verbose_name="Hauteur")
    # observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    fond = models.ForeignKey("self", verbose_name="Fond", on_delete=models.PROTECT, blank=True, null=True)
    defaut = models.BooleanField(verbose_name="Modèle par défaut", default=False)
    objets = models.TextField(verbose_name="Objets", blank=True, null=True)
    #iddonnee = models.IntegerField(db_column='IDdonnee', blank=True, null=True)  # Field name made lowercase.
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'documents_modeles'
        verbose_name = "modèle de document"
        verbose_name_plural = "modèles de documents"

    def __str__(self):
        return self.nom



class QuestionnaireQuestion(models.Model):
    idquestion = models.AutoField(verbose_name="ID", db_column='IDquestion', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=LISTE_CATEGORIES_QUESTIONNAIRES)
    ordre = models.IntegerField(verbose_name="Ordre")
    visible = models.BooleanField(verbose_name="Visible sur le bureau", default=True)
    label = models.CharField(verbose_name="Label", max_length=250)
    controle = models.CharField(verbose_name="contrôle", max_length=200, choices=[(ctrl["code"], ctrl["label"]) for ctrl in LISTE_CONTROLES_QUESTIONNAIRES])
    choix = models.CharField(verbose_name="Choix", max_length=500, blank=True, null=True, help_text="Saisissez les choix possibles séparés par un point-virgule. Exemple : 'Bananes;Pommes;Poires'")
    options = models.CharField(verbose_name="Options", max_length=250, blank=True, null=True)
    visible_portail = models.BooleanField(verbose_name="Visible sur le portail", default=False)
    visible_fiche_renseignement = models.BooleanField(verbose_name="Visible sur les fiches de renseignements", default=False)
    texte_aide = models.CharField(verbose_name="Texte d'aide", max_length=500, blank=True, null=True, help_text="Vous pouvez saisir un texte d'aide qui apparaîtra sous le champ de saisie.")
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'questionnaire_questions'
        verbose_name = "question de questionnaire"
        verbose_name_plural = "questions de questionnaires"

    def __str__(self):
        return self.label

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre
        liste_objects = QuestionnaireQuestion.objects.filter(categorie=self.categorie).order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1


class QuestionnaireReponse(models.Model):
    idreponse = models.AutoField(verbose_name="ID", db_column='IDreponse', primary_key=True)
    question = models.ForeignKey(QuestionnaireQuestion, verbose_name="Question", on_delete=models.CASCADE)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.CASCADE)
    famille = models.ForeignKey(Famille, verbose_name="Famille", blank=True, null=True, on_delete=models.CASCADE)
    collaborateur = models.ForeignKey("Collaborateur", verbose_name="Collaborateur", blank=True, null=True, on_delete=models.CASCADE)
    reponse = models.CharField(verbose_name="Réponse", max_length=450, blank=True, null=True)
    # type = models.CharField(verbose_name="Type", max_length=200, choices=LISTE_CATEGORIES_QUESTIONNAIRES, blank=True, null=True)
    donnee = models.IntegerField(verbose_name="Donnée associée", db_column='IDdonnee', blank=True, null=True)

    class Meta:
        db_table = 'questionnaire_reponses'
        verbose_name = "réponse de questionnaire"
        verbose_name_plural = "réponses de questionnaires"

    def __str__(self):
        return self.reponse

    def Get_reponse_for_ctrl(self):
        if self.question.controle in ("liste_deroulante", "liste_coches"):
            return self.reponse.split(";")
        if self.question.controle in ("entier", "slider"):
            if self.reponse:
                return int(self.reponse)
        if self.question.controle == "case_coche":
            return self.reponse == "True"
        if self.question.controle in ("decimal", "montant"):
            return decimal.Decimal(self.reponse or "0.0")
        return self.reponse

    def Get_reponse_fr(self):
        if not self.reponse:
            return ""
        if self.question.controle in ("liste_deroulante", "liste_coches"):
            return ", ".join(self.reponse.split(";"))
        if self.question.controle in ("entier", "slider") and self.reponse:
            return str(self.reponse)
        if self.question.controle == "case_coche":
            return "oui" if self.reponse == "True" else "non"
        if self.question.controle in ("decimal", "montant"):
            return float(decimal.Decimal(self.reponse or 0.0))
        return self.reponse or ""


class MemoJournee(models.Model):
    idmemo = models.AutoField(verbose_name="ID", db_column='IDmemo', primary_key=True)
    inscription = models.ForeignKey(Inscription, verbose_name="Inscription", on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Date")
    texte = models.CharField(verbose_name="Texte", max_length=450, blank=True, null=True)

    class Meta:
        db_table = 'memo_journee'
        verbose_name = "mémo journalier"
        verbose_name_plural = "mémos journaliers"

    def __str__(self):
        return "MemoJournee ID%d" % self.idmemo


class ModeleEmail(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column='IDmodele', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_MODELES_EMAILS)
    nom = models.CharField(verbose_name="Nom", max_length=250)
    description = models.CharField(verbose_name="Description", max_length=400, blank=True, null=True)
    objet = models.CharField(verbose_name="Objet", max_length=300, blank=True, null=True)
    html = models.TextField(verbose_name="Texte", blank=True, null=True)
    defaut = models.BooleanField(verbose_name="Modèle par défaut", default=False)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'modeles_emails'
        verbose_name = "modèle d'email"
        verbose_name_plural = "modèles d'emails"

    def __str__(self):
        return self.nom if self.idmodele else "Nouveau modèle"

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(ModeleEmail.objects.filter(categorie=self.categorie, defaut=True)) == 0:
            objet = ModeleEmail.objects.filter(categorie=self.categorie).first()
            if objet != None:
                objet.defaut = True
                objet.save()


class ModeleSMS(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column='IDmodele', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_MODELES_SMS)
    nom = models.CharField(verbose_name="Nom", max_length=250)
    description = models.CharField(verbose_name="Description", max_length=400, blank=True, null=True)
    objet = models.CharField(verbose_name="Objet", max_length=300, blank=True, null=True)
    texte = models.TextField(verbose_name="Texte", blank=True, null=True)
    defaut = models.BooleanField(verbose_name="Modèle par défaut", default=False)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'modeles_sms'
        verbose_name = "modèle de SMS"
        verbose_name_plural = "modèles de SMS"

    def __str__(self):
        return "ModeleSMS ID%d" % self.idmodele if self.idmodele else "Nouveau modèle"

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(ModeleSMS.objects.filter(categorie=self.categorie, defaut=True)) == 0:
            objet = ModeleSMS.objects.first(categorie=self.categorie)
            if objet != None:
                objet.defaut = True
                objet.save()


class Parametre(models.Model):
    idparametre = models.AutoField(verbose_name="ID", db_column='IDparametre', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, blank=True, null=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    parametre = models.TextField(verbose_name="Paramètre", blank=True, null=True)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.CASCADE)
    structure = models.ForeignKey(Structure, verbose_name="Structure", blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'parametres'
        verbose_name = "Paramètre"
        verbose_name_plural = "Paramètres"

    def __str__(self):
        return self.nom if self.nom else "Nouveau Paramètre"


class Payeur(models.Model):
    idpayeur = models.AutoField(verbose_name="ID", db_column='IDpayeur', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE)
    nom = models.CharField(verbose_name="Nom", max_length=300)

    class Meta:
        db_table = 'payeurs'
        verbose_name = "Payeur"
        verbose_name_plural = "Payeurs"

    def __str__(self):
        return self.nom if self.nom else "Nouveau"


class Depot(models.Model):
    iddepot = models.AutoField(verbose_name="ID", db_column='IDdepot', primary_key=True)
    date = models.DateField(verbose_name="Date")
    nom = models.CharField(verbose_name="Nom", max_length=200)
    verrouillage = models.BooleanField(verbose_name="Verrouillage", default=False)
    compte = models.ForeignKey(CompteBancaire, verbose_name="Compte bancaire", on_delete=models.PROTECT)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    code_compta = models.CharField(verbose_name="Code comptable", max_length=200, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0, blank=True, null=True)

    class Meta:
        db_table = 'depots'
        verbose_name = "Dépôt"
        verbose_name_plural = "Dépôts"

    def __str__(self):
        if self.nom and self.date:
            return "%s (%s)" % (self.nom, utils_dates.ConvertDateToFR(self.date))
        return self.nom if self.nom else "Nouveau dépôt"

    def Maj_montant(self):
        self.montant = Reglement.objects.filter(depot=self).aggregate(Sum("montant"))["montant__sum"]
        self.save()


class Reglement(models.Model):
    idreglement = models.AutoField(verbose_name="ID", db_column='IDreglement', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    date = models.DateField(verbose_name="Date")
    mode = models.ForeignKey(ModeReglement, verbose_name="Mode de règlement", on_delete=models.PROTECT)
    emetteur = models.ForeignKey(Emetteur, verbose_name="Emetteur", blank=True, null=True, on_delete=models.PROTECT)
    numero_piece = models.CharField(verbose_name="N° pièce", max_length=200, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    payeur = models.ForeignKey(Payeur, verbose_name="Payeur", on_delete=models.PROTECT)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    numero_quittancier = models.CharField(verbose_name="N° quittancier", max_length=100, blank=True, null=True)
    # idprestation_frais = models.IntegerField(verbose_name="ID", db_column='IDprestation_frais', blank=True, null=True)  # Field name made lowercase.
    compte = models.ForeignKey(CompteBancaire, verbose_name="Compte bancaire", on_delete=models.PROTECT)
    date_differe = models.DateField(verbose_name="Date d'encaissement différé", blank=True, null=True)
    encaissement_attente = models.BooleanField(verbose_name="Encaissement en attente", default=False)
    depot = models.ForeignKey(Depot, verbose_name="Dépôt", blank=True, null=True, on_delete=models.PROTECT)
    date_saisie = models.DateField(verbose_name="Date de création", auto_now_add=True)
    # idutilisateur = models.IntegerField(verbose_name="ID", db_column='IDutilisateur', blank=True, null=True)  # Field name made lowercase.
    # idprelevement = models.IntegerField(verbose_name="ID", db_column='IDprelevement', blank=True, null=True)  # Field name made lowercase.
    avis_depot = models.DateField(verbose_name="Date de l'avis d'encaissement", blank=True, null=True)
    # idpiece = models.IntegerField(verbose_name="ID", db_column='IDpiece', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'reglements'
        verbose_name = "Règlement"
        verbose_name_plural = "Règlements"

    def __str__(self):
        return "Règlement ID%d" % self.idreglement if self.idreglement else "Nouveau"

    def delete(self, *args, **kwargs):
        # Avant la suppression
        if self.depot:
            return "La suppression de '%s' est impossible car ce règlement est déjà inclus dans un dépôt" % self
        # Supprime l'objet
        super().delete(*args, **kwargs)


class Ventilation(models.Model):
    idventilation = models.AutoField(verbose_name="ID", db_column='IDventilation', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    reglement = models.ForeignKey(Reglement, verbose_name="Règlement", on_delete=models.CASCADE)
    prestation = models.ForeignKey(Prestation, verbose_name="Prestation", on_delete=models.CASCADE)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'ventilation'
        verbose_name = "Ventilation"
        verbose_name_plural = "Ventilations"

    def __str__(self):
        return "Ventilation ID%d" % self.idventilation if self.idventilation else "Nouveau"


class Recu(models.Model):
    idrecu = models.AutoField(verbose_name="ID", db_column='IDrecu', primary_key=True)
    numero = models.IntegerField(verbose_name="Numéro")
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    date_edition = models.DateField(verbose_name="Date d'édition")
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.PROTECT)
    reglement = models.ForeignKey(Reglement, verbose_name="Règlement", on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        db_table = 'recus'
        verbose_name = "Reçu de règlement"
        verbose_name_plural = "Reçus de règlements"

    def __str__(self):
        return "Reçu ID%d" % self.idrecu if self.idrecu else "Nouveau"


class Attestation(models.Model):
    idattestation = models.AutoField(verbose_name="ID", db_column='IDattestation', primary_key=True)
    numero = models.IntegerField(verbose_name="Numéro", blank=True, null=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    date_edition = models.DateField(verbose_name="Date d'édition")
    activites = models.CharField(verbose_name="Activités associées", max_length=200, blank=True, null=True)
    individus = models.CharField(verbose_name="Individus associés", max_length=200, blank=True, null=True)
    filtre_prestations = models.CharField(verbose_name="Filtre prestations", max_length=300, blank=True, null=True)
    exclusions_prestations = models.CharField(verbose_name="Exclusion prestations", max_length=300, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    total = models.DecimalField(verbose_name="Total", max_digits=10, decimal_places=2, default=0.0)
    regle = models.DecimalField(verbose_name="Réglé", max_digits=10, decimal_places=2, default=0.0)
    solde = models.DecimalField(verbose_name="Solde", max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'attestations'
        verbose_name = "attestation"
        verbose_name_plural = "attestations"

    def __str__(self):
        return "Attestation ID%d" % self.idattestation


class Devis(models.Model):
    iddevis = models.AutoField(verbose_name="ID", db_column='IDdevis', primary_key=True)
    numero = models.IntegerField(verbose_name="Numéro", blank=True, null=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    date_edition = models.DateField(verbose_name="Date d'édition")
    activites = models.CharField(verbose_name="Activités associées", max_length=200, blank=True, null=True)
    individus = models.CharField(verbose_name="Individus associés", max_length=200, blank=True, null=True)
    # idutilisateur = models.IntegerField(verbose_name="ID", db_column='IDutilisateur', blank=True, null=True)  # Field name made lowercase.
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    total = models.DecimalField(verbose_name="Total", max_digits=10, decimal_places=2, default=0.0)
    regle = models.DecimalField(verbose_name="Réglé", max_digits=10, decimal_places=2, default=0.0)
    solde = models.DecimalField(verbose_name="Solde", max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'devis'
        verbose_name = "devis"
        verbose_name_plural = "devis"

    def __str__(self):
        return "Devis ID%d" % self.iddevis


class Historique(models.Model):
    idaction = models.AutoField(verbose_name="ID", db_column='IDaction', primary_key=True)
    horodatage = models.DateTimeField(verbose_name="Horodatage", auto_now_add=True)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.PROTECT)
    famille = models.ForeignKey(Famille, verbose_name="Famille", blank=True, null=True, on_delete=models.CASCADE)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.CASCADE)
    collaborateur = models.ForeignKey("Collaborateur", verbose_name="Collaborateur", blank=True, null=True, on_delete=models.CASCADE)
    titre = models.CharField(verbose_name="Action", max_length=300, blank=True, null=True)
    detail = encrypt(models.TextField(verbose_name="Détail", blank=True, null=True))
    old = encrypt(models.TextField(verbose_name="Ancienne valeur", blank=True, null=True))
    objet = models.CharField(verbose_name="Objet", max_length=300, blank=True, null=True)
    idobjet = models.IntegerField(verbose_name="ID objet", blank=True, null=True)
    classe = models.CharField(verbose_name="Classe objet", max_length=300, blank=True, null=True)
    portail = models.BooleanField(verbose_name="Portail", default=False)
    date_lecture = models.DateTimeField(verbose_name="Date de lecture", blank=True, null=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité associée", on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateField(verbose_name="Date associée", blank=True, null=True)

    class Meta:
        db_table = 'historique'
        verbose_name = "Historique"
        verbose_name_plural = "Historique"

    def __str__(self):
        return "Historique ID%d" % self.idaction


class FiltreListe(models.Model):
    idfiltre = models.AutoField(verbose_name="ID", db_column='IDfiltre', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=400)
    parametres = models.TextField(verbose_name="Paramètres", blank=True, null=True)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.CASCADE)

    class Meta:
        db_table = 'filtres_listes'
        verbose_name = "Filtre de liste"
        verbose_name_plural = "Filtres de listes"

    def __str__(self):
        return "Filtre de liste ID%d" % self.idfiltre if self.idfiltre else "Nouveau"


class LotRappels(models.Model):
    idlot = models.AutoField(verbose_name="ID", db_column='IDlot', primary_key=True)
    nom = models.CharField(verbose_name="Nom du lot", max_length=200)

    class Meta:
        db_table = 'lots_rappels'
        verbose_name = "lot de rappels"
        verbose_name_plural = "lots de rappels"

    def __str__(self):
        return self.nom if self.nom else "Nouveau lot de rappels"


class ModeleRappel(models.Model):
    idtexte = models.AutoField(verbose_name="ID", db_column='IDtexte', primary_key=True)
    label = models.CharField(verbose_name="Nom", max_length=300)
    couleur = models.CharField(verbose_name="Couleur", max_length=100)
    retard_min = models.IntegerField(verbose_name="Nbre de jours min", blank=True, null=True)
    retard_max = models.IntegerField(verbose_name="Nbre de jours max", blank=True, null=True)
    titre = models.CharField(verbose_name="Titre", max_length=300)
    html = models.TextField(verbose_name="Texte", blank=True, null=True)

    class Meta:
        db_table = 'textes_rappels'
        verbose_name = "texte de rappels"
        verbose_name_plural = "textes de rappels"

    def __str__(self):
        return self.label if self.label else "Nouveau texte de rappels"


class Rappel(models.Model):
    idrappel = models.AutoField(verbose_name="ID", db_column='IDrappel', primary_key=True)
    numero = models.IntegerField(verbose_name="Numéro")
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT, blank=True, null=True)
    date_edition = models.DateField(verbose_name="Date")
    activites = models.CharField(verbose_name="Activités associées", max_length=200, blank=True, null=True)
    # idutilisateur = models.IntegerField(db_column='IDutilisateur', blank=True, null=True)
    modele = models.ForeignKey(ModeleRappel, verbose_name="Modèle de rappel", on_delete=models.PROTECT)
    date_reference = models.DateField(verbose_name="Date de référence")
    solde = models.DecimalField(verbose_name="Solde", max_digits=10, decimal_places=2, default=0.0)
    lot = models.ForeignKey(LotRappels, verbose_name="Lot de rappels", on_delete=models.PROTECT, blank=True, null=True)
    prestations = models.CharField(verbose_name="Types de prestations", max_length=200, blank=True, null=True)
    date_min = models.DateField(verbose_name="Date de début", blank=True, null=True)
    date_max = models.DateField(verbose_name="Date de fin", blank=True, null=True)

    class Meta:
        db_table = 'rappels'
        verbose_name = "rappel"
        verbose_name_plural = "rappels"

    def __str__(self):
        return "Rappel ID%d" % self.idrappel


class Lien(models.Model):
    idlien = models.AutoField(verbose_name="ID", db_column='IDlien', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE, blank=True, null=True)
    individu_sujet = models.ForeignKey(Individu, verbose_name="Individu sujet", related_name="individu_sujet", blank=True, null=True, on_delete=models.CASCADE)
    idtype_lien = models.IntegerField(verbose_name="Type de lien", blank=True, null=True)
    individu_objet = models.ForeignKey(Individu, verbose_name="Individu objet", related_name="individu_objet", blank=True, null=True, on_delete=models.CASCADE)
    responsable = models.BooleanField(verbose_name="Responsable", default=False)
    autorisation = models.IntegerField(verbose_name="Type d'autorisation", blank=True, null=True, choices=CHOIX_AUTORISATIONS)

    class Meta:
        db_table = 'liens'
        verbose_name = "lien"
        verbose_name_plural = "liens"

    def __str__(self):
        return "Lien ID%d" % self.idlien


class Contact(models.Model):
    idcontact = models.AutoField(verbose_name="ID", db_column='IDcontact', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    prenom = models.CharField(verbose_name="Prénom", max_length=200, blank=True, null=True)
    rue_resid = encrypt(models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True))
    cp_resid = encrypt(models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True))
    ville_resid = encrypt(models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True))
    tel_domicile = encrypt(models.CharField(verbose_name="Tél domicile", max_length=100, blank=True, null=True))
    tel_mobile = encrypt(models.CharField(verbose_name="Tél portable", max_length=100, blank=True, null=True))
    mail = encrypt(models.EmailField(verbose_name="Email", max_length=300, blank=True, null=True))
    site = models.CharField(verbose_name="Site", max_length=200, blank=True, null=True)
    memo = models.TextField(verbose_name="Mémo", blank=True, null=True)

    class Meta:
        db_table = 'contacts'
        verbose_name = "contact"
        verbose_name_plural = "contacts"

    def __str__(self):
        return "%s %s" % (self.nom, self.prenom if self.prenom else "")

    def Get_nom(self):
        texte = self.nom
        if self.prenom:
            texte += " " + self.prenom
        return texte



class PieceJointe(models.Model):
    idpiece_jointe = models.AutoField(verbose_name="ID", db_column='IDpiece_jointe', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    fichier = models.FileField(verbose_name="Fichier", upload_to=get_uuid_path, blank=True, null=True)

    class Meta:
        db_table = 'pieces_jointes'
        verbose_name = "pièce jointe"
        verbose_name_plural = "pièces jointes"

    def __str__(self):
        return "Pièce jointe ID%d" % self.idpiece_jointe


class DocumentJoint(models.Model):
    iddocument = models.AutoField(verbose_name="ID", db_column='IDdocument', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    fichier = models.FileField(verbose_name="Fichier", upload_to=get_uuid_path, blank=True, null=True)

    class Meta:
        db_table = 'documents_joints'
        verbose_name = "document joint"
        verbose_name_plural = "document joints"

    def __str__(self):
        return "Document joint ID%d" % self.iddocument


class Destinataire(models.Model):
    iddestinataire = models.AutoField(verbose_name="ID", db_column='IDdestinataire', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=300, blank=True, null=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.CASCADE)
    famille = models.ForeignKey(Famille, verbose_name="Famille", blank=True, null=True, on_delete=models.CASCADE)
    collaborateur = models.ForeignKey("Collaborateur", verbose_name="Collaborateur", blank=True, null=True, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, verbose_name="Contact", blank=True, null=True, on_delete=models.CASCADE)
    liste_diffusion = models.ForeignKey(ListeDiffusion, verbose_name="Liste de diffusion", blank=True, null=True, on_delete=models.CASCADE)
    adresse = encrypt(models.EmailField(verbose_name="Email", max_length=300, blank=True, null=True))
    documents = models.ManyToManyField(DocumentJoint, verbose_name="Documents joints", blank=True)
    date_envoi = models.DateTimeField(verbose_name="Date d'envoi", blank=True, null=True)
    resultat_envoi = models.CharField(verbose_name="Résultat de l'envoi", max_length=300, blank=True, null=True)
    valeurs = models.TextField(verbose_name="Valeurs", blank=True, null=True)

    class Meta:
        db_table = 'destinataires'
        verbose_name = "destinataire"
        verbose_name_plural = "destinataires"

    def __str__(self):
        return "Destinataire ID%d" % self.iddestinataire if self.iddestinataire else "Nouveau"


class Mail(models.Model):
    idmail = models.AutoField(verbose_name="ID", db_column='IDmail', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, blank=True, null=True)
    objet = models.CharField(verbose_name="Objet", max_length=300, blank=True, null=True)
    html = models.TextField(verbose_name="Texte", blank=True, null=True)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.CASCADE)
    adresse_exp = models.ForeignKey(AdresseMail, verbose_name="Expéditeur", blank=True, null=True, on_delete=models.SET_NULL)
    pieces_jointes = models.ManyToManyField(PieceJointe, verbose_name="Pièces jointes", blank=True)
    destinataires = models.ManyToManyField(Destinataire, verbose_name="Destinataires", blank=True)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    selection = models.CharField(verbose_name="Sélection", max_length=200, choices=[
        ("NON_ENVOYE", "Uniquemement les destinataires qui n'ont pas déjà reçu le message"),
        ("NON_ENVOYE_10", "Uniquemement les 10 premiers destinataires qui n'ont pas déjà reçu le message"),
        ("NON_ENVOYE_50", "Uniquemement les 50 premiers destinataires qui n'ont pas déjà reçu le message"),
        ("NON_ENVOYE_100", "Uniquemement les 100 premiers destinataires qui n'ont pas déjà reçu le message"),
        ("TOUS", "Tous les destinataires")],
        default="NON_ENVOYE")
    verrouillage_destinataires = models.BooleanField(verbose_name="Verrouillages des destinataires", default=False)

    class Meta:
        db_table = 'mails'
        verbose_name = "Email"
        verbose_name_plural = "Emails"

    def __str__(self):
        return "Email du %s : %s" % (self.date_creation.strftime('%d/%m/%Y %H:%m') if self.date_creation else "X", self.objet if self.objet else "Sans objet")

    def delete(self, *args, **kwargs):
        self.destinataires.all().delete()
        self.pieces_jointes.all().delete()
        super().delete(*args, **kwargs)


class PortailPeriode(models.Model):
    idperiode = models.AutoField(verbose_name='ID', db_column='IDperiode', primary_key=True)
    activite = models.ForeignKey(Activite, verbose_name="Activité", on_delete=models.CASCADE)
    nom = models.CharField(verbose_name="Nom de la période", max_length=200)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    choix_type_date = [("TOUTES", "Toutes les dates"), ("VACANCES", "Uniquement les dates de vacances"), ("SCOLAIRES", "Uniquement les dates scolaires")]
    type_date = models.CharField(verbose_name="Type de date", max_length=100, choices=choix_type_date, default="TOUTES")
    choix_affichage = [("TOUJOURS", "Toujours afficher"), ("JAMAIS", "Ne pas afficher"), ("PERIODE", "Afficher sur la période suivante")]
    affichage = models.CharField(verbose_name="Affichage", max_length=100, choices=choix_affichage, default="TOUJOURS")
    affichage_date_debut = models.DateTimeField(verbose_name="Début", blank=True, null=True)
    affichage_date_fin = models.DateTimeField(verbose_name="Fin", blank=True, null=True)
    modele = models.ForeignKey(ModeleEmail, verbose_name="Modèle d'Email", blank=True, null=True, on_delete=models.PROTECT)
    introduction = models.TextField(verbose_name="Introduction", blank=True, null=True)
    prefacturation = models.BooleanField(verbose_name="Activer la préfacturation pour cette période", default=False, help_text="Cochez cette case pour que la famille puisse payer les prestations de cette période sur le portail même si aucune facture n'a été générée.")
    choix_categories = [("TOUTES", "Toutes les catégories de compte internet"), ("AUCUNE", "Uniquement les catégories de compte internet non renseignées"), ("SELECTION", "Uniquement les catégories suivantes")]
    types_categories = models.CharField(verbose_name="Filtre catégories", max_length=100, choices=choix_categories, default="TOUTES")
    categories = models.ManyToManyField(CategorieCompteInternet, verbose_name="Sélection de catégories", related_name="periode_categories", blank=True)
    choix_villes = [("TOUTES", "Toutes les villes de résidence"), ("SELECTION", "Uniquement les familles résidant sur les villes suivantes"), ("SELECTION_INVERSE", "Uniquement les familles ne résidant pas sur les villes suivantes")]
    types_villes = models.CharField(verbose_name="Filtre villes", max_length=100, choices=choix_villes, default="TOUTES")
    villes = models.CharField(verbose_name="Sélection de villes", max_length=400, blank=True, null=True)
    mode_consultation = models.BooleanField(verbose_name="Mode consultation", default=False, help_text="Cochez cette case pour que les familles puissent uniquement consulter les réservations de la période sans pouvoir les modifier.")

    class Meta:
        db_table = 'portail_periodes'
        verbose_name = "période de réservation"
        verbose_name_plural = "périodes de réservation"

    def __str__(self):
        return "Période de réservation %s" % self.nom if self.nom else "Nouveau"

    def Is_active_today(self):
        """ Vérifie si la période est active ce jour """
        return self.affichage == "TOUJOURS" or (datetime.datetime.now() >= self.affichage_date_debut and datetime.datetime.now() <= self.affichage_date_fin)

    def Is_famille_authorized(self, famille=None):
        """ Vérifie si une famille est autorisée à accéder à cette période """
        # Vérification du compte internet
        if (self.types_categories == "AUCUNE" and famille.internet_categorie) or (self.types_categories == "SELECTION" and famille.internet_categorie not in self.categories.all()):
            return False
        # Vérification de la ville de résidence
        if self.types_villes != "TOUTES" and self.villes:
            liste_villes = [ville.strip().upper() for ville in self.villes.split(",")]
            if not famille.ville_resid or (self.types_villes == "SELECTION" and famille.ville_resid.upper() not in liste_villes) or (self.types_villes == "SELECTION_INVERSE" and famille.ville_resid.upper() in liste_villes):
                return False
        return True


class PortailParametre(models.Model):
    idparametre = models.AutoField(verbose_name="ID", db_column='IDparametre', primary_key=True)
    code = models.CharField(verbose_name="Code", max_length=200, blank=True, null=True)
    valeur = models.TextField(verbose_name="Valeur", blank=True, null=True)

    class Meta:
        db_table = 'portail_parametres'
        verbose_name = "paramètre de portail"
        verbose_name_plural = "paramètres de portail"

    def __str__(self):
        return "Paramètre de portail ID%d" % self.idparametre if self.idparametre else "Nouveau"


class PortailRenseignement(models.Model):
    idrenseignement = models.AutoField(verbose_name="ID", db_column='IDrenseignement', primary_key=True)
    date = models.DateTimeField(verbose_name="Date de modification", auto_now_add=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.CASCADE)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200)
    code = models.CharField(verbose_name="Code", max_length=200)
    nouvelle_valeur = encrypt(models.TextField(verbose_name="Nouvelle valeur", blank=True, null=True))
    ancienne_valeur = encrypt(models.TextField(verbose_name="Ancienne valeur", blank=True, null=True))
    choix_etat = [("ATTENTE", "En attente de validation"), ("VALIDE", "Validé"), ("REFUS", "Refusé")]
    etat = models.CharField(verbose_name="Etat", max_length=100, choices=choix_etat, default="ATTENTE")
    traitement_utilisateur = models.ForeignKey(Utilisateur, verbose_name="Traité par", blank=True, null=True, on_delete=models.PROTECT)
    traitement_date = models.DateTimeField(verbose_name="Date du traitement", blank=True, null=True)
    validation_auto = models.BooleanField(verbose_name="Validation automatique", default=True)
    idobjet = models.IntegerField(verbose_name="ID objet", blank=True, null=True)

    class Meta:
        db_table = 'portail_renseignements'
        verbose_name = "renseignement de portail"
        verbose_name_plural = "renseignements de portail"

    def __str__(self):
        return "Renseignement de portail ID%d" % self.idrenseignement if self.idrenseignement else "Nouveau"


class PortailChamp(models.Model):
    idchamp = models.AutoField(verbose_name="ID", db_column='IDchamp', primary_key=True)
    page = models.CharField(verbose_name="Page", max_length=200, blank=True, null=True)
    code = models.CharField(verbose_name="Code", max_length=200, blank=True, null=True)
    choix_etat = [("MASQUER", "Masqué"), ("AFFICHER", "Affiché"), ("MODIFIABLE", "Modifiable")]
    representant = models.CharField(verbose_name="Représentant", max_length=100, choices=choix_etat, default="MODIFIABLE")
    enfant = models.CharField(verbose_name="Enfant", max_length=100, choices=choix_etat, default="MODIFIABLE")
    contact = models.CharField(verbose_name="Contact", max_length=100, choices=choix_etat, default="MODIFIABLE")
    famille = models.CharField(verbose_name="Famille", max_length=100, choices=choix_etat, default="MODIFIABLE")

    class Meta:
        db_table = 'portail_champs'
        verbose_name = "champ de portail"
        verbose_name_plural = "champs de portail"

    def __str__(self):
        return "Champ de portail ID%d" % self.idchamp if self.idchamp else "Nouveau"


class PortailMessage(models.Model):
    idmessage = models.AutoField(verbose_name="ID", db_column='IDmessage', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.CASCADE)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.PROTECT)
    texte = models.TextField(verbose_name="Texte")
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    date_lecture = models.DateTimeField(verbose_name="Date de lecture", max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'portail_messages'
        verbose_name = "message"
        verbose_name_plural = "messages"

    def __str__(self):
        return "Message ID%d" % self.idmessage if self.idmessage else "Nouveau message"


class ContactUrgence(models.Model):
    idcontact = models.AutoField(verbose_name="ID", db_column='IDcontact', primary_key=True)
    nom = models.CharField(verbose_name=_("Nom"), max_length=200)
    prenom = models.CharField(verbose_name=_("Prénom"), max_length=200)
    rue_resid = encrypt(models.CharField(verbose_name=_("Rue"), max_length=200, blank=True, null=True))
    cp_resid = encrypt(models.CharField(verbose_name=_("Code postal"), max_length=50, blank=True, null=True))
    ville_resid = encrypt(models.CharField(verbose_name=_("Ville"), max_length=200, blank=True, null=True))
    tel_domicile = encrypt(models.CharField(verbose_name=_("Tél domicile"), max_length=100, blank=True, null=True))
    tel_mobile = encrypt(models.CharField(verbose_name=_("Tél portable"), max_length=100, blank=True, null=True))
    tel_travail = encrypt(models.CharField(verbose_name=_("Tél travail"), max_length=100, blank=True, null=True))
    mail = encrypt(models.EmailField(verbose_name=_("Email"), max_length=300, blank=True, null=True))
    observations = encrypt(models.TextField(verbose_name=_("Observations"), blank=True, null=True))
    lien = encrypt(models.CharField(verbose_name=_("Lien avec l'individu"), max_length=200))
    autorisation_sortie = models.BooleanField(verbose_name=_("Autorisé à récupérer l'individu"), default=True)
    autorisation_appel = models.BooleanField(verbose_name=_("A contacter en cas d'urgence"), default=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.CASCADE)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE)

    class Meta:
        db_table = 'contacts_urgence'
        verbose_name = "contact d'urgence et de sortie"
        verbose_name_plural = "contacts d'urgence et de sortie"

    def __str__(self):
        return "%s %s" % (self.nom, self.prenom if self.prenom else "")

    def Get_nom(self):
        texte = self.nom
        if self.prenom:
            texte += " " + self.prenom
        return texte

    def Get_autorisations(self):
        autorisations = []
        if self.autorisation_sortie:
            autorisations.append("""<span class='badge badge-success' title="Autorisé à récupérer l'individu"><i class='fa fa-sign-out margin-r-5'></i>Sortie</span>""")
        if self.autorisation_appel:
            autorisations.append("""<span class='badge badge-success' title="Contacter en cas d'urgence"><i class='fa fa-phone margin-r-5'></i>Urgence</span>""")
        return " ".join(autorisations)


class Assurance(models.Model):
    idassurance = models.AutoField(verbose_name="ID", db_column='IDassurance', primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", on_delete=models.PROTECT)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    assureur = models.ForeignKey(Assureur, verbose_name=_("Assureur"), on_delete=models.PROTECT)
    num_contrat = encrypt(models.CharField(verbose_name=_("N° de contrat"), max_length=200))
    date_debut = models.DateField(verbose_name=_("Date de début"))
    date_fin = models.DateField(verbose_name=_("Date de fin"), blank=True, null=True)
    document = models.FileField(verbose_name=_("Document"), storage=get_storage("assurance"), upload_to=get_uuid_path, blank=True, null=True, help_text="Vous pouvez ajouter un document (PDF ou image).")

    class Meta:
        db_table = 'assurances'
        verbose_name = "assurance"
        verbose_name_plural = "assurances"

    def __str__(self):
        texte = "Assurance %s" % self.assureur
        if self.date_fin:
            texte += " du %s au %s" % (utils_dates.ConvertDateToFR(self.date_debut), utils_dates.ConvertDateToFR(self.date_fin))
        else:
            texte += " à partir du %s" % utils_dates.ConvertDateToFR(self.date_debut)
        return texte

    def get_upload_path(self):
        return str(self.individu_id)


class Mandat(models.Model):
    idmandat = models.AutoField(verbose_name="ID", db_column='IDmandat', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", related_name="mandats", on_delete=models.PROTECT)
    rum = models.CharField(verbose_name="RUM", max_length=100, help_text="Référence Unique du Mandat.")
    choix_type = [("RECURRENT", "Récurrent"), ("PONCTUEL", "Ponctuel")]
    type = models.CharField(verbose_name="Type", max_length=100, choices=choix_type, default="RECURRENT", help_text="Le mandat est généralement de type récurrent.")
    date = models.DateField(verbose_name="Date", help_text="Date de signature du mandat.")
    individu = models.ForeignKey(Individu, verbose_name="Titulaire", on_delete=models.PROTECT, blank=True, null=True, help_text="Titulaire du compte bancaire. Sélectionnez 'Autre individu' si le titulaire n'est pas dans la liste proposée.")
    individu_nom = models.CharField(verbose_name="Nom", max_length=200, blank=True, null=True)
    individu_rue = encrypt(models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True))
    individu_cp = encrypt(models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True))
    individu_ville = encrypt(models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True))
    iban = encrypt(models.CharField(verbose_name="IBAN", max_length=27, help_text="La cohérence de l'IBAN est vérifié lors de l'enregistrement du mandat."))
    bic = encrypt(models.CharField(verbose_name="BIC", max_length=11, help_text="La cohérence du BIC est vérifié lors de l'enregistrement du mandat."))
    memo = models.TextField(verbose_name="Observations", blank=True, null=True)
    choix_sequences = [
        ("OOFF", "Prélèvement ponctuel (OOFF)"), ("FRST", "Premier prélèvement d'une série (FRST)"),
        ("RCUR", "Prélèvement suivant d'une série (RCUR)"), ("FNAL", "Dernier prélèvement d'une série (FNAL)")
    ]
    sequence = models.CharField(verbose_name="Séquence", max_length=100, choices=choix_sequences, default="RCUR", help_text="La prochaine séquence est généralement définie sur RCUR lors de la création du mandat.")
    actif = models.BooleanField(verbose_name="Mandat actif", default=True, help_text="Décochez la case pour désactiver ce mandat.")
    structures = models.ManyToManyField(Structure, verbose_name="Structures associées", related_name="mandat_structures", blank=True, help_text="Ce mandat ne sera utilisé que pour les structures sélectionnées.")

    class Meta:
        db_table = 'mandats'
        verbose_name = "mandat"
        verbose_name_plural = "mandats"

    def __str__(self):
        return "Mandat n°%s" % self.rum if self.idmandat else "<nouveau>"

    def Actualiser(self, ajouter=False):
        """ ajouter : si ajout de prélèvement """
        if ajouter:
            if self.sequence == "FRST":
                self.sequence = "RCUR"
                self.save()
            if self.sequence == "OOFF":
                self.actif = False
                self.save()
        else:
            # Recherche les prélèvements pes existants avec ce mandat
            nbre_prelevements_pes = PesPiece.objects.filter(prelevement_mandat=self).count()
            if self.sequence == "RCUR" and not nbre_prelevements_pes:
                self.sequence = "FRST"
                self.save()


class PesModele(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column="IDmodele", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    format = models.CharField(verbose_name="Format", max_length=100, choices=CHOIX_FORMAT_EXPORT_TRESOR)
    compte = models.ForeignKey(CompteBancaire, verbose_name="Compte à créditer", on_delete=models.PROTECT, help_text="Sélectionnez le compte bancaire à créditer dans le cadre du règlement automatique.")
    id_poste = models.CharField(verbose_name="Poste comptable par défaut", max_length=200, blank=True, null=True)
    id_collectivite = models.CharField(verbose_name="ID Collectivité", max_length=200, blank=True, null=True)
    code_collectivite = models.CharField(verbose_name="Code collectivité", max_length=200, blank=True, null=True)
    code_budget = models.CharField(verbose_name="Code budget", max_length=10, blank=True, null=True)
    code_prodloc = models.CharField(verbose_name="Code produit local par défaut", max_length=4, blank=True, null=True)
    code_etab = models.CharField(verbose_name="Code établissement", max_length=200, blank=True, null=True)
    service1 = models.CharField(verbose_name="Service axe 1", max_length=15, blank=True, null=True, help_text="Premier axe analytique.")
    service2 = models.CharField(verbose_name="Service axe 2", max_length=10, blank=True, null=True, help_text="Second axe analytique.")
    operation = models.CharField(verbose_name="Opération comptable", max_length=10, blank=True, null=True)
    fonction = models.CharField(verbose_name="Fonction comptable", max_length=10, blank=True, null=True)
    prelevement_libelle = models.CharField(verbose_name="Libellé du prélèvement", max_length=450, default="{NOM_ORGANISATEUR} - Facture {NUM_FACTURE}", help_text="Saisissez le libellé du prélèvement qui apparaîtra sur le relevé de compte de la famille. Vous pouvez personnaliser ce libellé grâce aux mots-clés suivants : {NOM_ORGANISATEUR}, {NUM_FACTURE}, {MOIS}, {MOIS_LETTRES}, {ANNEE}, {DATE_DEBUT_MOIS}, {DATE_FIN_MOIS}, {PRESTATION_DATE_MIN}, {PRESTATION_DATE_MAX}, {PRESTATION_DEBUT_MOIS}, {PRESTATION_FIN_MOIS}, {PRESTATION_MOIS}, {PRESTATION_ANNEE}.")
    objet_piece = models.CharField(verbose_name="Libellé de la pièce", max_length=450, default="Facture {NUM_FACTURE} - {MOIS_LETTRES} {ANNEE}", help_text="Saisissez l'objet de la pièce par défaut. Vous pouvez personnaliser ce libellé grâce aux mots-clés suivants : {NOM_ORGANISATEUR}, {NUM_FACTURE}, {MOIS}, {MOIS_LETTRES}, {ANNEE}, {DATE_DEBUT_MOIS}, {DATE_FIN_MOIS}, {PRESTATION_DATE_MIN}, {PRESTATION_DATE_MAX}, {PRESTATION_DEBUT_MOIS}, {PRESTATION_FIN_MOIS}, {PRESTATION_MOIS}, {PRESTATION_ANNEE}.")
    prestation_libelle = models.CharField(verbose_name="Libellé de la prestation", max_length=450, default="{INDIVIDU_PRENOM} - {PRESTATION_LABEL}", help_text="Saisissez le libellé de la prestation par défaut. Vous pouvez personnaliser ce libellé grâce aux mots-clés suivants : {ACTIVITE_NOM}, {ACTIVITE_ABREGE}, {PRESTATION_LABEL}, {PRESTATION_QUANTITE}, {PRESTATION_MOIS}, {PRESTATION_ANNEE}, {INDIVIDU_NOM}, {INDIVIDU_PRENOM}, {MOIS}, {MOIS_LETTRES}, {ANNEE}, {DATE_DEBUT_MOIS}, {DATE_FIN_MOIS}.")
    nom_collectivite = models.CharField(verbose_name="Nom de la collectivité", max_length=450, blank=True, null=True, default="{NOM_ORGANISATEUR}", help_text="Saisissez le nom de la collectivité (Par défaut : {NOM_ORGANISATEUR}).")
    reglement_auto = models.BooleanField(verbose_name="Règlement automatique", default=False, help_text="Cochez cette case si vous souhaitez que Noethys créé un règlement automatiquement pour les prélèvements.")
    mode = models.ForeignKey(ModeReglement, verbose_name="Mode de règlement", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez le mode de règlement à utiliser dans le cadre du règlement automatique.")
    payable_internet = models.BooleanField(verbose_name="Titre payable par internet", default=True, help_text="Cochez cette case si l'usager peut payer sur internet avec PayFip.")
    choix_edition_asap = [
        ("", "ASAP non dématérialisé"),
        ("01", "01-ASAP dématérialisé à éditer par le centre éditique"),
        ("02", "02-ASAP dématérialisé à destination d'une entité publique référencée dans Chorus Pro"),
        ("03", "03-ASAP ORMC Chorus Pro"),
        ("04", "04-ASAP sans traitement DGFIP"),
    ]
    edition_asap = models.CharField(verbose_name="Edition ASAP", max_length=100, choices=choix_edition_asap, default="01", blank=True, null=True, help_text="Indiquez si l'ASAP doit être édité ou non par le centre éditique (Balise Edition dans bloc pièce du PES Titre).")
    nom_tribunal = models.CharField(verbose_name="Nom du tribunal", max_length=400, blank=True, null=True, default="le tribunal administratif", help_text="Saisissez le nom du tribunal administratif de recours.")
    inclure_detail = models.BooleanField(verbose_name="Inclure le détail des factures", default=True, help_text="Cochez cette case si vous souhaitez que Noethys intègre le détail des prestations de chaque facture.")
    inclure_pieces_jointes = models.BooleanField(verbose_name="Inclure les factures au format PDF", default=True, help_text="Cochez cette case si vous souhaitez que Noethys intègre les factures au format PDF.")
    code_compta_as_alias = models.BooleanField(verbose_name="Utiliser le code comptable familial comme code tiers", default=True, help_text="Utiliser le code comptable de la famille (Fiche famille > Onglet Divers) comme code tiers (ou alias). Sinon un code de type FAM000001 sera généré automatiquement.")
    modele_document = models.ForeignKey(ModeleDocument, verbose_name="Modèle de document", on_delete=models.PROTECT, blank=True, null=True)
    inclure_tiers_solidaires = models.BooleanField(verbose_name="Inclure les tiers solidaires", default=True, help_text="Cochez cette case si vous souhaitez que Noethys intègre les tiers solidaires.")

    class Meta:
        db_table = 'pes_modeles'
        verbose_name = "modèle d'export"
        verbose_name_plural = "modèles d'export"

    def __str__(self):
        return self.nom if self.nom else "Nouveau modèle"



class PesLot(models.Model):
    idlot = models.AutoField(verbose_name="ID", db_column='IDlot', primary_key=True)
    modele = models.ForeignKey(PesModele, verbose_name="Modèle d'export", on_delete=models.PROTECT)
    nom = models.CharField(verbose_name="Nom de l'export", max_length=200, help_text="Nom interne à l'application. Exemple : Restauration - Janvier 2021.")
    # verrouillage = models.BooleanField(verbose_name="Verrouillage", default=False)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    exercice = models.IntegerField(verbose_name="Exercice")
    mois = models.IntegerField(verbose_name="Mois", choices=LISTE_MOIS)
    # objet_piece = models.CharField(verbose_name="Objet de l'écriture", max_length=450, help_text="Ce texte est utilisé comme libellé de l'écriture. Exemple : Restauration - Janvier 2021. Vous pouvez personnaliser ce libellé grâce aux mots-clés suivants : {NOM_ORGANISATEUR}, {NUM_FACTURE}, {MOIS}, {MOIS_LETTRES}, {ANNEE}.")
    # prestation_libelle = models.CharField(verbose_name="Libellé de la prestation", max_length=450, default="{INDIVIDU_PRENOM} - {PRESTATION_LABEL}", help_text="Saisissez le libellé de la prestation. Vous pouvez personnaliser ce libellé grâce aux mots-clés suivants : {ACTIVITE_NOM}, {ACTIVITE_ABREGE}, {PRESTATION_LABEL}, {PRESTATION_QUANTITE}, {PRESTATION_MOIS}, {PRESTATION_ANNEE}, {INDIVIDU_NOM}, {INDIVIDU_PRENOM}, {MOIS}, {MOIS_LETTRES}, {ANNEE}.")
    date_emission = models.DateField(verbose_name="Date d'émission")
    date_prelevement = models.DateField(verbose_name="Date de prélèvement")
    date_envoi = models.DateField(verbose_name="Date d'envoi")
    id_bordereau = models.CharField(verbose_name="Identifiant du bordereau", max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'pes_lots'
        verbose_name = "lot"
        verbose_name_plural = "lots"

    def __str__(self):
        return self.nom if self.nom else "Nouvel export"


class PesPiece(models.Model):
    idpiece = models.AutoField(verbose_name="ID", db_column='IDpiece', primary_key=True)
    lot = models.ForeignKey(PesLot, verbose_name="Lot", on_delete=models.PROTECT)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    prelevement = models.BooleanField(verbose_name="Prélèvement", default=False)
    prelevement_mandat = models.ForeignKey(Mandat, verbose_name="Mandat", blank=True, null=True, on_delete=models.PROTECT)
    prelevement_sequence = models.CharField(verbose_name="Séquence", blank=True, null=True, choices=[("OOFF", "Prélèvement ponctuel (OOFF)"), ("FRST", "Premier prélèvement d'une série (FRST)"), ("RCUR", "Prélèvement suivant d'une série (RCUR)"), ('FNAL', "Dernier prélèvement d'une série (FNAL)")], max_length=100)
    prelevement_statut = models.CharField(verbose_name="Statut du prélèvement", choices=[("valide", "Valide"), ("refus", "Refus"), ("attente", "Attente")], default="attente", max_length=100)
    prelevement_reglement = models.ForeignKey(Reglement, verbose_name="Règlement", on_delete=models.SET_NULL, blank=True, null=True)
    titulaire_helios = models.ForeignKey(Individu, verbose_name="Titulaire Hélios", related_name="piece_titulaire_helios", on_delete=models.PROTECT)
    tiers_solidaire = models.ForeignKey(Individu, verbose_name="Tiers solidaire", related_name="piece_tiers_solidaire", on_delete=models.PROTECT, blank=True, null=True)
    type = models.CharField(verbose_name="Type de pièce", choices=[("facture", "Facture"), ("manuel", "Manuel")], max_length=100, default="facture")
    facture = models.ForeignKey(Facture, verbose_name="Facture", on_delete=models.PROTECT, blank=True, null=True)
    # numero = models.IntegerField(blank=True, null=True)
    # libelle = models.CharField(verbose_name="Libellé de la pièce", max_length=400, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'pes_pieces'
        verbose_name = "pièce d'export"
        verbose_name_plural = "pièces d'export"

    def __str__(self):
        return "Pièce d'export ID%d" % self.idpiece if self.idpiece else "Nouvelle pièce"


class Consentement(models.Model):
    idconsentement = models.AutoField(verbose_name="ID", db_column='IDconsentement', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT, blank=True, null=True)
    unite_consentement = models.ForeignKey(UniteConsentement, verbose_name="Unité de consentement", on_delete=models.PROTECT)
    horodatage = models.DateTimeField(verbose_name="Date", auto_now_add=True)

    class Meta:
        db_table = 'consentements'
        verbose_name = "consentement"
        verbose_name_plural = "consentements"

    def __str__(self):
        return "Consentement ID%d" % self.idconsentement


class Album(models.Model):
    idalbum = models.AutoField(verbose_name="ID", db_column='IDalbum', primary_key=True)
    titre = models.CharField(verbose_name="Titre de l'album", max_length=300, help_text="Le titre est visible pour les familles sur le portail.")
    description = models.TextField(verbose_name="Description", blank=True, null=True, help_text="La description est visible pour les familles sur le portail.")
    auteur = models.ForeignKey(Utilisateur, verbose_name="Auteur", blank=True, null=True, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    code = models.CharField(verbose_name="Code de l'album", max_length=300, default=get_uuid)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'albums'
        verbose_name = "album"
        verbose_name_plural = "albums"

    def __str__(self):
        return self.titre if self.titre else "Nouvel album"


class Photo(models.Model):
    idphoto = models.AutoField(verbose_name="ID", db_column='IDphoto', primary_key=True)
    album = models.ForeignKey(Album, verbose_name="Album", on_delete=models.PROTECT)
    fichier = models.FileField(verbose_name="Fichier", storage=get_storage("photo"), upload_to=get_uuid_path)
    titre = models.CharField(verbose_name="Titre de la photo", max_length=300, blank=True, null=True, help_text="Le titre est visible pour les familles sur le portail.")
    date_creation = models.DateTimeField(verbose_name="Date de création", blank=True, null=True, help_text="Cette date est utilisée pour trier les photos.")

    class Meta:
        db_table = 'photos'
        verbose_name = "photo"
        verbose_name_plural = "photos"

    def __str__(self):
        return "Photo ID%d" % self.idphoto if self.idphoto else "Nouvelle photo"

    def get_upload_path(self):
        return str(self.album_id)


class ImageArticle(models.Model):
    idimage = models.AutoField(verbose_name="ID", db_column='IDimage', primary_key=True)
    titre = models.CharField(verbose_name="Titre", max_length=300)
    image = models.ImageField(verbose_name="Image", upload_to=get_uuid_path)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'images_articles'
        verbose_name = "image"
        verbose_name_plural = "images"

    def __str__(self):
        return self.titre if self.idimage else "Nouvelle image"


class Article(models.Model):
    idarticle = models.AutoField(verbose_name="ID", db_column='IDarticle', primary_key=True)
    titre = models.CharField(verbose_name="Titre", max_length=300)
    texte = models.TextField(verbose_name="Texte")
    image = models.ImageField(verbose_name="Image", upload_to=get_uuid_path, blank=True, null=True)
    image_article = models.ForeignKey(ImageArticle, verbose_name="Image", blank=True, null=True, on_delete=models.SET_NULL)
    auteur = models.ForeignKey(Utilisateur, verbose_name="Auteur", blank=True, null=True, on_delete=models.CASCADE)
    date_debut = models.DateTimeField(verbose_name="Début de publication", help_text="Saisissez la date de début de publication. Par défaut, la date du jour de la création de l'article.")
    date_fin = models.DateTimeField(verbose_name="Fin de publication", blank=True, null=True, help_text="Laissez vide pour ne pas définir de date de fin de publication.")
    choix_couleur = [(None, "Par défaut"), ("primary", "Bleu foncé"), ("info", "Bleu clair"), ("success", "Vert"), ("warning", "Jaune"), ("danger", "Rouge"), ("gray", "Gris")]
    couleur_fond = models.CharField(verbose_name="Couleur de fond", max_length=100, choices=choix_couleur, default=None, blank=True, null=True, help_text="Couleur de fond du cadre de l'article. Blanc par défaut.")
    choix_statut = [("publie", "Publié"), ("non_publie", "Non publié")]
    statut = models.CharField(verbose_name="Statut", max_length=100, choices=choix_statut, default="publie", help_text="Sélectionnez Non publié pour interrompre la publication quelque soit la date de fin de publication prévue.")
    document = models.FileField(verbose_name="Document", upload_to=get_uuid_path, blank=True, null=True, help_text="Privilégiez un document au format PDF.")
    document_titre = models.CharField(verbose_name="Titre", max_length=300, default="Document", help_text="Saisissez un nom de document.")
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)
    choix_public = [("toutes", "Toutes les familles"),
                    ("inscrits", "Les familles dont un membre est inscrit à l'une des activités suivantes"),
                    ("presents", "Les familles dont un membre est présent sur l'une des activités suivantes et sur la période suivante"),
                    ("presents_groupes", "Les familles dont un membre est présent sur l'un des groupes suivants et sur la période suivante"),
                    ]
    public = models.CharField(verbose_name="Public", max_length=100, choices=choix_public, help_text="Sélectionnez le public qui pourra consulter cet article.")
    activites = models.ManyToManyField(Activite, verbose_name="Activités", related_name="article_activites", blank=True, help_text="Sélectionnez une ou plusieurs activités dans la liste.")
    groupes = models.ManyToManyField(Groupe, verbose_name="Groupes", related_name="article_groupes", blank=True, help_text="Sélectionnez un ou plusieurs groupes dans la liste.")
    present_debut = models.DateField(verbose_name="Date de début", blank=True, null=True)
    present_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    album = models.ForeignKey(Album, verbose_name="Album photos", blank=True, null=True, on_delete=models.SET_NULL, help_text="Sélectionnez un album photos existant à joindre à cet article.")
    texte_popup = models.TextField(verbose_name="Texte", blank=True, null=True, help_text="Ce texte sera affiché dans une fenêtre popup sur la page d'accueil. A utiliser uniquement pour les informations importantes.")
    sondage = models.ForeignKey("Sondage", verbose_name="Formulaire", blank=True, null=True, on_delete=models.SET_NULL, help_text="Sélectionnez un formulaire existant à joindre à cet article.")

    class Meta:
        db_table = 'articles'
        verbose_name = "article"
        verbose_name_plural = "articles"

    def __str__(self):
        return self.titre if self.idarticle else "Nouvel article"

    def Get_anciennete(self):
        return (datetime.datetime.now().date() - self.date_debut.date()).days


class ImageFond(models.Model):
    idimage = models.AutoField(verbose_name="ID", db_column='IDimage', primary_key=True)
    titre = models.CharField(verbose_name="Titre", max_length=300)
    image = models.ImageField(verbose_name="Image", upload_to=get_uuid_path)

    class Meta:
        db_table = 'images_fond'
        verbose_name = "image de fond"
        verbose_name_plural = "images de fond"

    def __str__(self):
        return self.titre if self.idimage else "Nouvelle image de fond"


class PortailDocument(models.Model):
    iddocument = models.AutoField(verbose_name="ID", db_column='IDdocument', primary_key=True)
    titre = models.CharField(verbose_name="Titre", max_length=200, help_text="Saisissez un titre pour ce document. Ex : Fiche d'inscription annuelle...")
    texte = models.CharField(verbose_name="Sous-titre", max_length=200, blank=True, null=True, help_text="Vous pouvez saisir un sous-titre. Ex : Version 2021...")
    choix_couleur = [("primary", "Bleu foncé"), ("info", "Bleu clair"), ("success", "Vert"), ("warning", "Jaune"), ("danger", "Rouge"), ("gray", "Gris")]
    couleur_fond = models.CharField(verbose_name="Couleur de fond", max_length=100, choices=choix_couleur, default="primary", help_text="Couleur de fond de l'icône. Bleu foncé par défaut.")
    document = models.FileField(verbose_name="Document", upload_to=get_uuid_path, help_text="Privilégiez un document au format PDF.")
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)
    type_piece = models.ForeignKey(TypePiece, verbose_name="Type de pièce", related_name="type_piece_document", on_delete=models.PROTECT, blank=True, null=True, help_text="Si ce document correspond à un type de pièce existant, sélectionnez-le dans la liste proposée.")

    class Meta:
        db_table = 'portail_documents'
        verbose_name = "document"
        verbose_name_plural = "documents"

    def __str__(self):
        return self.titre if self.iddocument else "Nouveau document"

    def Get_extension(self):
        return os.path.splitext(self.document.name)[1].replace(".", "")


class DestinataireSMS(models.Model):
    iddestinataire = models.AutoField(verbose_name="ID", db_column='IDdestinataire', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=300, blank=True, null=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.CASCADE)
    famille = models.ForeignKey(Famille, verbose_name="Famille", blank=True, null=True, on_delete=models.CASCADE)
    collaborateur = models.ForeignKey("Collaborateur", verbose_name="Collaborateur", blank=True, null=True, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, verbose_name="Contact", blank=True, null=True, on_delete=models.CASCADE)
    mobile = encrypt(models.EmailField(verbose_name="Mobile", max_length=300, blank=True, null=True))
    date_envoi = models.DateTimeField(verbose_name="Date d'envoi", blank=True, null=True)
    resultat_envoi = models.CharField(verbose_name="Résultat de l'envoi", max_length=300, blank=True, null=True)
    valeurs = encrypt(models.TextField(verbose_name="Valeurs", blank=True, null=True))

    class Meta:
        db_table = 'destinataires_sms'
        verbose_name = "destinataire SMS"
        verbose_name_plural = "destinataires SMS"

    def __str__(self):
        return "Destinataire ID%d" % self.iddestinataire if self.iddestinataire else "Nouveau"


class SMS(models.Model):
    idsms = models.AutoField(verbose_name="ID", db_column='IDsms', primary_key=True)
    objet = models.CharField(verbose_name="Objet", max_length=300, blank=True, null=True)
    texte = models.TextField(verbose_name="Texte", blank=True, null=True)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.CASCADE)
    configuration_sms = models.ForeignKey(ConfigurationSMS, verbose_name="Configuration", blank=True, null=True, on_delete=models.SET_NULL)
    destinataires = models.ManyToManyField(DestinataireSMS, verbose_name="Destinataires", blank=True)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    selection = models.CharField(verbose_name="Sélection", max_length=200, choices=[
        ("NON_ENVOYE", "Uniquemement les destinataires qui n'ont pas déjà reçu le message"),
        ("NON_ENVOYE_10", "Uniquemement les 10 premiers destinataires qui n'ont pas déjà reçu le message"),
        ("NON_ENVOYE_50", "Uniquemement les 50 premiers destinataires qui n'ont pas déjà reçu le message"),
        ("NON_ENVOYE_100", "Uniquemement les 100 premiers destinataires qui n'ont pas déjà reçu le message"),
        ("TOUS", "Tous les destinataires")],
        default="NON_ENVOYE")
    verrouillage_destinataires = models.BooleanField(verbose_name="Verrouillages des destinataires", default=False)

    class Meta:
        db_table = 'sms'
        verbose_name = "SMS"
        verbose_name_plural = "SMS"

    def __str__(self):
        return "SMS du %s : %s" % (self.date_creation.strftime('%d/%m/%Y %H:%m') if self.date_creation else "X", self.objet if self.objet else "Sans objet")

    def delete(self, *args, **kwargs):
        self.destinataires.all().delete()
        super().delete(*args, **kwargs)


class Perception(models.Model):
    idperception = models.AutoField(verbose_name="ID", db_column='IDperception', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    rue_resid = models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True)
    cp_resid = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville_resid = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'perceptions'
        verbose_name = "perception"
        verbose_name_plural = "perceptions"

    def __str__(self):
        return self.nom


class PrelevementsModele(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column="IDmodele", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    format = models.CharField(verbose_name="Format", max_length=100, choices=CHOIX_FORMAT_PRELEVEMENTS)
    compte = models.ForeignKey(CompteBancaire, verbose_name="Compte à créditer", on_delete=models.PROTECT, help_text="Sélectionnez le compte bancaire à créditer.")
    mode = models.ForeignKey(ModeReglement, verbose_name="Mode de règlement", blank=True, null=True, on_delete=models.PROTECT, help_text="Sélectionnez le mode de règlement à utiliser.")
    reglement_auto = models.BooleanField(verbose_name="Règlement automatique", default=False, help_text="Cochez cette case si vous souhaitez que Noethysweb créé un règlement automatiquement.")
    encodage = models.CharField(verbose_name="Encodage", max_length=100, choices=[("utf-8", "UTF-8"), ("iso-8859-15", "ISO-8859-15")], default="utf-8", help_text="Sélectionnez le format souhaité")
    perception = models.ForeignKey(Perception, verbose_name="Perception", on_delete=models.PROTECT, blank=True, null=True)
    identifiant_service = models.CharField(verbose_name="Identifiant du service", max_length=200, blank=True, null=True, help_text="Saisissez l'identifiant du service. Exemple : TGDFT027 (numéro de département sur 3 chiffres).")
    poste_comptable = models.CharField(verbose_name="Poste comptable par défaut", max_length=200, blank=True, null=True, help_text="Saisissez le codique de la DDFiP de rattachement sur 6 caractères. Exemple : 027000")

    class Meta:
        db_table = 'modeles_prelevements'
        verbose_name = "modèle de lot de prélèvements"
        verbose_name_plural = "modèles de lot de prélèvements"

    def __str__(self):
        return self.nom if self.nom else "Nouveau modèle"


class PrelevementsLot(models.Model):
    idlot = models.AutoField(verbose_name="ID", db_column='IDlot', primary_key=True)
    modele = models.ForeignKey(PrelevementsModele, verbose_name="Modèle de lot", on_delete=models.PROTECT)
    nom = models.CharField(verbose_name="Nom du lot", max_length=200, help_text="Nom interne à l'application. Exemple : Restauration - Janvier 2021.")
    date = models.DateField(verbose_name="Date de prélèvement")
    # verrouillage = models.BooleanField(verbose_name="Verrouillage", default=False)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    motif = models.CharField(verbose_name="Motif", max_length=300, blank=True, null=True, help_text="Saisissez le motif du prélèvement. Ex : 'Garderie Novembre 2019'.")
    numero_sequence = models.IntegerField(verbose_name="Numéro de séquence", default=1, blank=True, null=True, help_text="Numéro de séquence du fichier dans une même journée. Exemple: 1 = premier fichier de la journée.")

    class Meta:
        db_table = 'lots_prelevements'
        verbose_name = "lot de prélèvements"
        verbose_name_plural = "lots de prélèvements"

    def __str__(self):
        return self.nom if self.nom else "Nouveau lot de prélèvements"


class Prelevements(models.Model):
    idprelevement = models.AutoField(verbose_name="ID", db_column='IDprelevement', primary_key=True)
    lot = models.ForeignKey(PrelevementsLot, verbose_name="Lot", on_delete=models.PROTECT)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    type = models.CharField(verbose_name="Type", choices=[("facture", "Facture"), ("manuel", "Manuel")], max_length=100, default="facture")
    facture = models.ForeignKey(Facture, verbose_name="Facture", on_delete=models.PROTECT, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2)
    mandat = models.ForeignKey(Mandat, verbose_name="Mandat", on_delete=models.PROTECT)
    sequence = models.CharField(verbose_name="Séquence", choices=[("OOFF", "Prélèvement ponctuel (OOFF)"), ("FRST", "Premier prélèvement d'une série (FRST)"), ("RCUR", "Prélèvement suivant d'une série (RCUR)"), ('FNAL', "Dernier prélèvement d'une série (FNAL)")], max_length=100)
    statut = models.CharField(verbose_name="Statut", choices=[("valide", "Valide"), ("refus", "Refus"), ("attente", "Attente")], default="attente", max_length=100)
    reglement = models.ForeignKey(Reglement, verbose_name="Règlement", on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        db_table = "prelevements"
        verbose_name = "prélèvement"
        verbose_name_plural = "prélèvements"

    def __str__(self):
        return "Prélèvement ID%d" % self.idprelevement if self.idprelevement else "Nouveau prélèvement"


class Lecture(models.Model):
    idlecture = models.AutoField(verbose_name="ID", db_column='IDlecture', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.CASCADE, blank=True, null=True)
    article = models.ForeignKey(Article, verbose_name="Article", on_delete=models.CASCADE)
    horodatage = models.DateTimeField(verbose_name="Date", auto_now_add=True)

    class Meta:
        db_table = 'lectures'
        verbose_name = "lecture"
        verbose_name_plural = "lectures"

    def __str__(self):
        return "Lecture ID%d" % self.idlecture


class Paiement(models.Model):
    idpaiement = models.AutoField(verbose_name="ID", db_column='IDpaiement', primary_key=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    idtransaction = models.CharField(verbose_name="ID transaction", max_length=50, blank=True, null=True)
    refdet = models.CharField(verbose_name="refdet", max_length=50, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    objet = models.CharField(verbose_name="objet", max_length=200, blank=True, null=True)
    saisie = models.CharField(verbose_name="Mode", max_length=50, blank=True, null=True)
    resultrans = models.CharField(verbose_name="resultrans", max_length=50, blank=True, null=True)
    numauto = models.CharField(verbose_name="numauto", max_length=50, blank=True, null=True)
    dattrans = models.CharField(verbose_name="dattrans", max_length=50, blank=True, null=True)
    heurtrans = models.CharField(verbose_name="heurtrans", max_length=50, blank=True, null=True)
    systeme_paiement = models.CharField(verbose_name="Système de paiement", max_length=50, blank=True, null=True)
    resultat = models.CharField(verbose_name="Résultat", max_length=50, blank=True, null=True)
    message = models.CharField(verbose_name="Message", max_length=450, blank=True, null=True)
    ventilation = models.TextField(verbose_name="ventilation", blank=True, null=True)
    horodatage = models.DateTimeField(verbose_name="Horodatage", auto_now_add=True)
    reglements = models.ManyToManyField(Reglement, verbose_name="Règlements", blank=True)
    notification = models.DateTimeField(verbose_name="Horodatage de la notification à l'utilisateur", blank=True, null=True)

    class Meta:
        db_table = 'paiements'
        verbose_name = "Paiement en ligne"
        verbose_name_plural = "Paiements en ligne"

    def __str__(self):
        return "Paiement ID%d" % self.idpaiement if self.idpaiement else "Nouveau"


class Tache_recurrente(models.Model):
    idtache_recurrente = models.AutoField(verbose_name="ID", db_column='IDtache_recurrente', primary_key=True)
    titre = models.CharField(verbose_name="Titre", max_length=250)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.CASCADE)
    structure = models.ForeignKey(Structure, verbose_name="Structure", blank=True, null=True, on_delete=models.SET_NULL)
    recurrence = models.CharField(verbose_name="Récurrence", max_length=250, blank=True, null=True)

    class Meta:
        db_table = 'taches_recurrentes'
        verbose_name = "tâche récurrente"
        verbose_name_plural = "tâches récurrentes"

    def __str__(self):
        return "Tâche récurrente ID%d" % self.idtache_recurrente if self.idtache_recurrente else "Nouveau"


class Tache(models.Model):
    idtache = models.AutoField(verbose_name="ID", db_column='IDtache', primary_key=True)
    tache_recurrente = models.ForeignKey(Tache_recurrente, verbose_name="Tâche récurrente", blank=True, null=True, on_delete=models.CASCADE)
    date = models.DateField(verbose_name="Date")
    titre = models.CharField(verbose_name="Titre", max_length=250)
    utilisateur = models.ForeignKey(Utilisateur, verbose_name="Utilisateur", blank=True, null=True, on_delete=models.CASCADE)
    structure = models.ForeignKey(Structure, verbose_name="Structure", blank=True, null=True, on_delete=models.SET_NULL)
    fait = models.BooleanField(verbose_name="Tâche effectuée", default=False)

    class Meta:
        db_table = 'taches'
        verbose_name = "tâche"
        verbose_name_plural = "tâches"

    def __str__(self):
        return "Tâche du %s" % self.date.strftime('%d/%m/%Y')


class LotAttestationsFiscales(models.Model):
    idlot = models.AutoField(verbose_name="ID", db_column='IDlot', primary_key=True)
    nom = models.CharField(verbose_name="Nom du lot", max_length=200)

    class Meta:
        db_table = 'lots_attestations_fiscales'
        verbose_name = "lot d'attestations fiscales"
        verbose_name_plural = "lots d'attestations fiscales'"

    def __str__(self):
        return self.nom if self.nom else "Nouveau lot d'attestations fiscales"


class AttestationFiscale(models.Model):
    idattestation = models.AutoField(verbose_name="ID", db_column='IDattestation', primary_key=True)
    numero = models.IntegerField(verbose_name="Numéro", blank=True, null=True)
    famille = models.ForeignKey(Famille, verbose_name="Famille", on_delete=models.PROTECT)
    date_edition = models.DateField(verbose_name="Date d'édition")
    activites = models.CharField(verbose_name="Activités associées", max_length=200, blank=True, null=True)
    individus = models.CharField(verbose_name="Individus associés", max_length=200, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    lot = models.ForeignKey(LotAttestationsFiscales, verbose_name="Lot d'attestations fiscales", on_delete=models.PROTECT, blank=True, null=True)
    total = models.DecimalField(verbose_name="Total", max_digits=10, decimal_places=2, default=0.0)
    detail = models.TextField(verbose_name="Détail", blank=True, null=True)

    class Meta:
        db_table = 'attestations_fiscales'
        verbose_name = "attestation fiscale"
        verbose_name_plural = "attestations fiscales"

    def __str__(self):
        return "Attestation fiscale ID%d" % self.idattestation


# class LocationsDemandes(models.Model):
#     iddemande = models.AutoField(db_column='IDdemande', primary_key=True, blank=True, null=True)  # Field name made lowercase.
#     date = models.DateTimeField(blank=True, null=True)
#     idfamille = models.IntegerField(db_column='IDfamille', blank=True, null=True)  # Field name made lowercase.
#     observations = models.TextField(verbose_name="Observations", blank=True, null=True)
#     categories = models.CharField(blank=True, null=True)
#     produits = models.CharField(blank=True, null=True)
#     statut = models.CharField(blank=True, null=True)
#     motif_refus = models.CharField(blank=True, null=True)
#     idlocation = models.IntegerField(db_column='IDlocation', blank=True, null=True)  # Field name made lowercase.
#
#     class Meta:
#         managed = False
#         db_table = 'locations_demandes'


class ComptaAnalytique(models.Model):
    idanalytique = models.AutoField(verbose_name="ID", db_column="IDanalytique", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    abrege = models.CharField(verbose_name="Abrégé", max_length=50, blank=True, null=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = "compta_analytiques"
        verbose_name = "poste analytique"
        verbose_name_plural = "postes analytiques"

    def __str__(self):
        return self.nom if self.nom else "Nouveau poste analytique"


class ComptaCompteComptable(models.Model):
    idcompte = models.AutoField(verbose_name="ID", db_column="IDcompte", primary_key=True)
    numero = models.CharField(verbose_name="Numéro", max_length=50, blank=True, null=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = "compta_comptes_comptables"
        verbose_name = "compte comptable"
        verbose_name_plural = "comptes comptables"

    def __str__(self):
        return self.nom if self.nom else "Nouveau compte comptable"


class ComptaCategorie(models.Model):
    idcategorie = models.AutoField(verbose_name="ID", db_column="IDcategorie", primary_key=True)
    type = models.CharField(verbose_name="Type", max_length=50, choices=[("debit", "Débit"), ("credit", "Crédit")])
    nom = models.CharField(verbose_name="Nom", max_length=200)
    abrege = models.CharField(verbose_name="Abrégé", max_length=50, blank=True, null=True)
    # journal = models.CharField(verbose_name="Journal", max_length=10, blank=True, null=True)
    compte_comptable = models.ForeignKey(ComptaCompteComptable, verbose_name="Compte comptable", on_delete=models.PROTECT, blank=True, null=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = "compta_categories"
        verbose_name = "catégorie comptable"
        verbose_name_plural = "catégories comptables"

    def __str__(self):
        return self.nom if self.nom else "Nouvelle catégorie comptable"


class ComptaTiers(models.Model):
    idtiers = models.AutoField(verbose_name="ID", db_column="IDtiers", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    # idcode_comptable = models.IntegerField(db_column='IDcode_comptable', blank=True, null=True)  # Field name made lowercase.
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = "compta_tiers"
        verbose_name = "tiers"
        verbose_name_plural = "tiers"

    def __str__(self):
        return self.nom if self.nom else "Nouveau tiers"


class ComptaReleve(models.Model):
    idreleve = models.AutoField(verbose_name="ID", db_column="IDreleve", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    compte = models.ForeignKey(CompteBancaire, verbose_name="Compte bancaire", on_delete=models.PROTECT)

    class Meta:
        db_table = "compta_releves"
        verbose_name = "relevé de compte"
        verbose_name_plural = "relevés de compte"

    def __str__(self):
        return self.nom if self.nom else "Nouveau relevé"


class ComptaVirement(models.Model):
    idvirement = models.AutoField(verbose_name="ID", db_column="IDvirement", primary_key=True)
    date = models.DateField(verbose_name="Date")
    libelle = models.CharField(verbose_name="Libellé", max_length=200, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    compte_debit = models.ForeignKey(CompteBancaire, verbose_name="Compte débiteur", related_name="virement_compte_debit", on_delete=models.CASCADE)
    compte_credit = models.ForeignKey(CompteBancaire, verbose_name="Compte créditeur", related_name="virement_compte_credit", on_delete=models.CASCADE)
    releve_debit = models.ForeignKey(ComptaReleve, verbose_name="Relevé débiteur", related_name="virement_releve_debit", on_delete=models.CASCADE, blank=True, null=True)
    releve_credit = models.ForeignKey(ComptaReleve, verbose_name="Relevé créditeur", related_name="virement_releve_credit", on_delete=models.CASCADE, blank=True, null=True)
    operation_debit = models.ForeignKey("ComptaOperation", verbose_name="Opération au débit", related_name="virement_operation_debit", on_delete=models.CASCADE, blank=True, null=True)
    operation_credit = models.ForeignKey("ComptaOperation", verbose_name="Opération au crédit", related_name="virement_operation_credit", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = "compta_virements"
        verbose_name = "virement"
        verbose_name_plural = "virements"

    def __str__(self):
        return "Virement ID%d" % self.idvirement


class ComptaOperation(models.Model):
    idoperation = models.AutoField(verbose_name="ID", db_column="IDoperation", primary_key=True)
    type = models.CharField(verbose_name="Type", max_length=50, choices=[("debit", "Débit"), ("credit", "Crédit")])
    date = models.DateField(verbose_name="Date")
    libelle = models.CharField(verbose_name="Libellé", max_length=200)
    tiers = models.ForeignKey(ComptaTiers, verbose_name="Tiers", on_delete=models.PROTECT, blank=True, null=True)
    mode = models.ForeignKey(ModeReglement, verbose_name="Mode de règlement", on_delete=models.PROTECT, blank=True, null=True)
    num_piece = models.CharField(verbose_name="Numéro de pièce", max_length=200, blank=True, null=True)
    ref_piece = models.CharField(verbose_name="Référence pièce", max_length=200, blank=True, null=True)
    compte = models.ForeignKey(CompteBancaire, verbose_name="Compte bancaire", on_delete=models.PROTECT)
    releve = models.ForeignKey(ComptaReleve, verbose_name="Relevé bancaire", on_delete=models.PROTECT, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    virement = models.ForeignKey(ComptaVirement, verbose_name="Virement", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = "compta_operations"
        verbose_name = "Opération de trésorerie"
        verbose_name_plural = "opérations de trésorerie"

    def __str__(self):
        return "Opération ID%d" % self.idoperation


class ComptaVentilation(models.Model):
    idventilation = models.AutoField(verbose_name="ID", db_column="IDventilation", primary_key=True)
    operation = models.ForeignKey(ComptaOperation, verbose_name="Opération", on_delete=models.CASCADE)
    categorie = models.ForeignKey(ComptaCategorie, verbose_name="Catégorie", on_delete=models.PROTECT)
    analytique = models.ForeignKey(ComptaAnalytique, verbose_name="Analytique", on_delete=models.PROTECT)
    libelle = models.CharField(verbose_name="Libellé", max_length=200, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)
    date_budget = models.DateField(verbose_name="Date budget")

    class Meta:
        db_table = "compta_ventilation"
        verbose_name = "Ventilation d'une opération"
        verbose_name_plural = "ventilations d'opérations"

    def __str__(self):
        return "Ventilation ID%d" % self.idventilation


class ComptaOperationBudgetaire(models.Model):
    idoperation_budgetaire = models.AutoField(verbose_name="ID", db_column="IDoperation_budgetaire", primary_key=True)
    type = models.CharField(verbose_name="Type", max_length=50, choices=[("debit", "Débit"), ("credit", "Crédit")])
    date_budget = models.DateField(verbose_name="Date budget")
    compte = models.ForeignKey(CompteBancaire, verbose_name="Compte bancaire", on_delete=models.PROTECT, blank=True, null=True)
    categorie = models.ForeignKey(ComptaCategorie, verbose_name="Catégorie", on_delete=models.PROTECT)
    analytique = models.ForeignKey(ComptaAnalytique, verbose_name="Analytique", on_delete=models.PROTECT)
    libelle = models.CharField(verbose_name="Libellé", max_length=200, blank=True, null=True)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        db_table = "compta_operations_budgetaires"
        verbose_name = "opération budgétaire"
        verbose_name_plural = "opérations budgétaires"

    def __str__(self):
        return "Opération budgétaire ID%d" % self.idoperation_budgetaire


class ComptaBudget(models.Model):
    idbudget = models.AutoField(verbose_name="ID", db_column="IDbudget", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    analytiques = models.ManyToManyField(ComptaAnalytique, verbose_name="Poste analytiques", related_name="postes_analytiques")
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = "compta_budgets"
        verbose_name = "budget"
        verbose_name_plural = "budgets"

    def __str__(self):
        return "Budget ID%d" % self.idbudget


class ComptaCategorieBudget(models.Model):
    idcategorie_budget = models.AutoField(verbose_name="ID", db_column="IDcategorie_budget", primary_key=True)
    budget = models.ForeignKey(ComptaBudget, verbose_name="Budget", on_delete=models.CASCADE)
    categorie = models.ForeignKey(ComptaCategorie, verbose_name="Catégorie", on_delete=models.PROTECT)
    montant = models.DecimalField(verbose_name="Montant", max_digits=10, decimal_places=2, default=0.0)

    class Meta:
        db_table = "compta_categories_budget"
        verbose_name = "catégorie budgétaire"
        verbose_name_plural = "catégories budgétaires"

    def __str__(self):
        return "Catégorie budgétaire ID%s" % (self.idcategorie_budget or "Nouvelle catégorie budgétaire")


class TypeQualificationCollaborateur(models.Model):
    idtype_qualification = models.AutoField(verbose_name="ID", db_column="IDtype_qualification", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)

    class Meta:
        db_table = "types_qualifications"
        verbose_name = "type de qualification"
        verbose_name_plural = "types de qualifications"

    def __str__(self):
        return self.nom


class TypePosteCollaborateur(models.Model):
    idtype_poste = models.AutoField(verbose_name="ID", db_column="IDtype_poste", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)

    class Meta:
        db_table = "types_postes_collaborateur"
        verbose_name = "type de poste"
        verbose_name_plural = "types de postes"

    def __str__(self):
        return self.nom


class TypePieceCollaborateur(models.Model):
    idtype_piece = models.AutoField(verbose_name="ID", db_column='IDtype_piece', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    duree_validite = models.CharField(verbose_name="Durée de validité", max_length=100, blank=True, null=True)
    obligatoire = models.CharField(verbose_name="Obligatoire", max_length=50, choices=[("OUI", "Oui"), ("NON", "Non"), ("QUALIFICATIONS", "Obligatoire pour les qualifications suivantes"), ("POSTES", "Obligatoire pour les postes suivants")], default="NON")
    qualifications = models.ManyToManyField(TypeQualificationCollaborateur, verbose_name="Qualifications associées", related_name="type_piece_qualifications", blank=True)
    postes = models.ManyToManyField(TypePosteCollaborateur, verbose_name="Postes associés", related_name="type_piece_postes", blank=True)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'types_pieces_collaborateur'
        verbose_name = "type de pièce"
        verbose_name_plural = "types de pièce"

    def __str__(self):
        return self.nom

    def Get_duree(self):
        return utils_dates.ConvertDureeStrToDuree(self.duree_validite)

    def Get_date_fin_validite(self, date_reference=None):
        if not date_reference:
            date_reference = datetime.date.today()
        if not self.duree_validite:
            return datetime.date(2999, 1, 1)
        if self.duree_validite.startswith("j"):
            return date_reference + self.Get_duree()
        if self.duree_validite.startswith("d"):
            return utils_dates.ConvertDateENGtoDate(self.duree_validite[1:])


class GroupeCollaborateurs(models.Model):
    idgroupe = models.AutoField(verbose_name="ID", db_column='IDgroupe', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    superviseurs = models.ManyToManyField(Utilisateur, verbose_name="Superviseurs", related_name="superviseurs_groupe_collaborateurs")

    class Meta:
        db_table = "groupes_collaborateurs"
        verbose_name = "groupe de collaborateurs"
        verbose_name_plural = "groupes de collaborateurs"

    def __str__(self):
        return self.nom if self.idgroupe else "Nouveau groupe de collaborateurs"


class Collaborateur(models.Model):
    idcollaborateur = models.AutoField(verbose_name="ID", db_column='IDcollaborateur', primary_key=True)
    civilite = models.CharField(verbose_name="Civilité", max_length=50, choices=[("M", "Monsieur"), ("MME", "Madame")], default="M")
    nom = models.CharField(verbose_name="Nom", max_length=200)
    nom_jfille = models.CharField(verbose_name="Nom de naissance", max_length=200, blank=True, null=True)
    prenom = models.CharField(verbose_name="Prénom", max_length=200, blank=True, null=True)
    rue_resid = encrypt(models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True))
    cp_resid = encrypt(models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True))
    ville_resid = encrypt(models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True))
    travail_tel = encrypt(models.CharField(verbose_name="Téléphone pro.", max_length=100, blank=True, null=True))
    travail_mail = encrypt(models.EmailField(verbose_name="Email pro.", max_length=300, blank=True, null=True))
    tel_domicile = encrypt(models.CharField(verbose_name="Tél domicile", max_length=100, blank=True, null=True))
    tel_mobile = encrypt(models.CharField(verbose_name="Tél portable", max_length=100, blank=True, null=True))
    mail = encrypt(models.EmailField(verbose_name="Email personnel", max_length=300, blank=True, null=True))
    memo = models.TextField(verbose_name="Mémo", blank=True, null=True)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    etat = models.CharField(verbose_name="Etat", max_length=50, blank=True, null=True)
    photo = models.ImageField(verbose_name="Photo", upload_to=get_uuid_path, blank=True, null=True)
    qualifications = models.ManyToManyField(TypeQualificationCollaborateur, verbose_name="Qualifications", related_name="collaborateur_qualifications", blank=True)
    groupes = models.ManyToManyField(GroupeCollaborateurs, verbose_name="Groupes associés", related_name="collaborateur_groupes", blank=True)

    class Meta:
        db_table = "collaborateurs"
        verbose_name = "collaborateur"
        verbose_name_plural = "collaborateurs"

    def __str__(self):
        return self.Get_nom()

    def Get_nom(self):
        return "%s %s" % (self.nom, self.prenom)

    def Get_photo(self, forTemplate=True):
        if self.photo:
            return self.photo.url
        nom_image = "homme.png" if self.civilite == "homme" else "femme.png"
        return static("images/" + nom_image) if forTemplate else settings.STATIC_ROOT + "/images/" + nom_image


class PieceCollaborateur(models.Model):
    idpiece = models.AutoField(verbose_name="ID", db_column='IDpiece', primary_key=True)
    type_piece = models.ForeignKey(TypePieceCollaborateur, verbose_name="Type de pièce", on_delete=models.PROTECT, blank=True, null=True)
    collaborateur = models.ForeignKey(Collaborateur, verbose_name="Collaborateur", on_delete=models.CASCADE, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Date de début", blank=True, null=True)
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    document = models.FileField(verbose_name="Document", storage=get_storage("piece_collaborateur"), upload_to=get_uuid_path, blank=True, null=True)
    titre = models.CharField(verbose_name="Titre", max_length=200, blank=True, null=True)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)

    class Meta:
        db_table = 'pieces_collaborateur'
        verbose_name = "pièce"
        verbose_name_plural = "pièces"

    def __str__(self):
        return self.Get_nom()

    def Get_nom(self):
        if not self.type_piece:
            return self.titre
        return self.type_piece.nom


class TypeEvenementCollaborateur(models.Model):
    idtype_evenement = models.AutoField(verbose_name="ID", db_column='IDtype_evenement', primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    type = models.CharField(verbose_name="Type", max_length=100, choices=[("ADDITION", "Temps comptabilisé"), ("NEUTRE", "Temps non comptabilisé"), ("SOUSTRACTION", "Temps soustrait")])
    chevauchement_possible = models.BooleanField(verbose_name="Chevauchement possible", default=False)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    couleur = models.CharField(verbose_name="Couleur", max_length=100, default="#3c8dbc")

    class Meta:
        db_table = "types_evenements_collaborateur"
        verbose_name = "catégorie d'évènement"
        verbose_name_plural = "catégories d'évènements"

    def __str__(self):
        return self.nom


class EvenementCollaborateur(models.Model):
    idevenement = models.AutoField(verbose_name="ID", db_column="IDevenement", primary_key=True)
    collaborateur = models.ForeignKey(Collaborateur, verbose_name="Collaborateur", on_delete=models.PROTECT, blank=True, null=True)
    type_evenement = models.ForeignKey(TypeEvenementCollaborateur, verbose_name="Catégorie", on_delete=models.PROTECT, blank=True, null=True)
    date_debut = models.DateTimeField(verbose_name="Début", blank=True, null=True)
    date_fin = models.DateTimeField(verbose_name="Fin", blank=True, null=True)
    titre = models.CharField(verbose_name="Titre", max_length=200, blank=True, null=True)

    class Meta:
        db_table = "evenements_collaborateur"
        verbose_name = "évènement d'un collaborateur"
        verbose_name_plural = "évènements d'un collaborateur"

    def __str__(self):
        return "Evenement ID%d" % self.idevenement if self.idevenement else "Nouvel évènement"


class ContratCollaborateur(models.Model):
    idcontrat = models.AutoField(verbose_name="ID", db_column="IDcontrat", primary_key=True)
    collaborateur = models.ForeignKey(Collaborateur, verbose_name="Collaborateur", on_delete=models.PROTECT)
    type_poste = models.ForeignKey(TypePosteCollaborateur, verbose_name="Poste", on_delete=models.PROTECT)
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin", blank=True, null=True)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)

    class Meta:
        db_table = "contrats_collaborateur"
        verbose_name = "contrat d'un collaborateur"
        verbose_name_plural = "contrats d'un collaborateur"

    def __str__(self):
        return "Contrat ID%d" % self.idcontrat if self.idcontrat else "Nouveau contrat"


class ModelePlanningCollaborateur(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column="IDmodele", primary_key=True)
    nom = models.CharField(verbose_name="Nom", max_length=300)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    inclure_feries = models.BooleanField(verbose_name="Inclure les jours fériés", default=False)

    class Meta:
        db_table = "modeles_planning_collaborateur"
        verbose_name = "modèle de planning"
        verbose_name_plural = "modèles de plannings"

    def __str__(self):
        return self.nom


class LigneModelePlanningCollaborateur(models.Model):
    idligne = models.AutoField(verbose_name="ID", db_column="IDligne", primary_key=True)
    modele = models.ForeignKey(ModelePlanningCollaborateur, verbose_name="Modèle de planning", on_delete=models.CASCADE)
    jour = models.IntegerField(verbose_name="Jour", choices=JOURS_COMPLETS_SEMAINE)
    periode = models.CharField(verbose_name="Période", max_length=50, choices=[("TOUTES", "Toutes les périodes"), ("SCOLAIRES", "Période scolaire"), ("VACANCES", "Période de vacances")], default="TOUTES")
    heure_debut = models.TimeField(verbose_name="Début")
    heure_fin = models.TimeField(verbose_name="Fin")
    type_evenement = models.ForeignKey(TypeEvenementCollaborateur, verbose_name="Catégorie", on_delete=models.PROTECT, blank=True, null=True)
    titre = models.CharField(verbose_name="Titre", max_length=200, blank=True, null=True)

    class Meta:
        db_table = "lignes_modeles_planning_collaborateur"
        verbose_name = "ligne de modèle de planning"
        verbose_name_plural = "lignes de modèles de planning"

    def __str__(self):
        return "Ligne de modèle ID%d" % self.idligne if self.idligne else "Nouvelle ligne de modèle"


class TransportLigne(models.Model):
    idligne = models.AutoField(verbose_name="ID", db_column="IDligne", primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_TRANSPORTS)
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = "transports_lignes"
        verbose_name = "ligne"
        verbose_name_plural = "lignes"

    def __str__(self):
        return self.nom if self.idligne else "Nouvelle ligne"


class TransportArret(models.Model):
    idarret = models.AutoField(verbose_name="ID", db_column="IDarret", primary_key=True)
    ligne = models.ForeignKey(TransportLigne, verbose_name="Ligne", on_delete=models.PROTECT)
    ordre = models.IntegerField(verbose_name="Ordre")
    nom = models.CharField(verbose_name="Nom", max_length=200)

    class Meta:
        db_table = "transports_arrets"
        verbose_name = "arrêt"
        verbose_name_plural = "arrêts"

    def __str__(self):
        return self.nom if self.idarret else "Nouvel arrêt"


class TransportCompagnie(models.Model):
    idcompagnie = models.AutoField(verbose_name="ID", db_column="IDcompagnie", primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_TRANSPORTS)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    rue = models.CharField(verbose_name="Rue", max_length=200, blank=True, null=True)
    cp = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)
    tel = models.CharField(verbose_name="Téléphone", max_length=200, blank=True, null=True)
    mail = models.EmailField(verbose_name="Email", max_length=300, blank=True, null=True)

    class Meta:
        db_table = "transports_compagnies"
        verbose_name = "compagnie"
        verbose_name_plural = "compagnies"

    def __str__(self):
        return self.nom if self.idcompagnie else "Nouvelle compagnie"


class TransportLieu(models.Model):
    idlieu = models.AutoField(verbose_name="ID", db_column="IDlieu", primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_TRANSPORTS)
    nom = models.CharField(verbose_name="Nom", max_length=200)
    cp = models.CharField(verbose_name="Code postal", max_length=50, blank=True, null=True)
    ville = models.CharField(verbose_name="Ville", max_length=200, blank=True, null=True)

    class Meta:
        db_table = "transports_lieux"
        verbose_name = "compagnie"
        verbose_name_plural = "compagnies"

    def __str__(self):
        return self.nom if self.idlieu else "Nouveau lieu"


class Transport(models.Model):
    idtransport = models.AutoField(verbose_name="ID", db_column="IDtransport", primary_key=True)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.PROTECT)
    mode = models.CharField(verbose_name="Mode", max_length=100)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_TRANSPORTS)
    compagnie = models.ForeignKey(TransportCompagnie, verbose_name="Compagnie", blank=True, null=True, on_delete=models.PROTECT)
    ligne = models.ForeignKey(TransportLigne, verbose_name="Ligne", blank=True, null=True, on_delete=models.PROTECT)
    numero = models.CharField(verbose_name="Numéro", max_length=200, blank=True, null=True)
    details = models.CharField(verbose_name="Détails", max_length=200, blank=True, null=True)
    observations = models.TextField(verbose_name="Observations", blank=True, null=True)
    depart_date = models.DateField(verbose_name="Date de départ", blank=True, null=True)
    depart_heure = models.TimeField(verbose_name="Heure de départ", blank=True, null=True)
    depart_arret = models.ForeignKey(TransportArret, verbose_name="Arrêt", related_name="transport_depart_arret", blank=True, null=True, on_delete=models.PROTECT)
    depart_lieu = models.ForeignKey(TransportLieu, verbose_name="Lieu", related_name="transport_depart_lieu", blank=True, null=True, on_delete=models.PROTECT)
    depart_localisation = models.CharField(verbose_name="Localisation", max_length=200, blank=True, null=True)
    arrivee_date = models.DateField(verbose_name="Date d'arrivée", blank=True, null=True)
    arrivee_heure = models.TimeField(verbose_name="Heure d'arrivée", blank=True, null=True)
    arrivee_arret = models.ForeignKey(TransportArret, verbose_name="Arrêt", related_name="transport_arrivee_arret", blank=True, null=True, on_delete=models.PROTECT)
    arrivee_lieu = models.ForeignKey(TransportLieu, verbose_name="Lieu", related_name="transport_arrivee_lieu", blank=True, null=True, on_delete=models.PROTECT)
    arrivee_localisation = models.CharField(verbose_name="Localisation", max_length=200, blank=True, null=True)
    date_debut = models.DateField(verbose_name="Début", blank=True, null=True)
    date_fin = models.DateField(verbose_name="Fin", blank=True, null=True)
    actif = models.BooleanField(verbose_name="Actif", default=True)
    jours_scolaires = MultiSelectField(verbose_name="Jours scolaires", max_length=100, choices=JOURS_SEMAINE, blank=True, null=True)
    jours_vacances = MultiSelectField(verbose_name="Jours de vacances", max_length=100, choices=JOURS_SEMAINE, blank=True, null=True)
    unites = models.ManyToManyField(Unite, verbose_name="Unités", related_name="unites_transports", blank=True)
    prog = models.ForeignKey("self", verbose_name="Programmation", on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        db_table = "transports"
        verbose_name = "transport"
        verbose_name_plural = "transports"

    def __str__(self):
        return "Transport ID%d" % self.idtransport if self.idtransport else "Nouveau transport"


class ModeleImpression(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column='IDmodele', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_MODELES_IMPRESSIONS)
    nom = models.CharField(verbose_name="Nom", max_length=250)
    description = models.CharField(verbose_name="Description", max_length=400, blank=True, null=True)
    modele_document = models.ForeignKey(ModeleDocument, verbose_name="Modèle de document", on_delete=models.PROTECT, blank=True, null=True)
    options = models.TextField(verbose_name="Options", blank=True, null=True)
    defaut = models.BooleanField(verbose_name="Modèle par défaut", default=False)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = "modeles_impressions"
        verbose_name = "modèle d'impression"
        verbose_name_plural = "modèles d'impressions"

    def __str__(self):
        return self.nom if self.idmodele else "Nouveau modèle"

    def delete(self, *args, **kwargs):
        # Supprime l'objet
        super().delete(*args, **kwargs)
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(ModeleImpression.objects.filter(categorie=self.categorie, defaut=True)) == 0:
            objet = ModeleImpression.objects.filter(categorie=self.categorie).first()
            if objet != None:
                objet.defaut = True
                objet.save()


class ModeleWord(models.Model):
    idmodele = models.AutoField(verbose_name="ID", db_column='IDmodele', primary_key=True)
    categorie = models.CharField(verbose_name="Catégorie", max_length=200, choices=CATEGORIES_MODELES_WORD)
    nom = models.CharField(verbose_name="Nom", max_length=250)
    description = models.CharField(verbose_name="Description", max_length=400, blank=True, null=True)
    fichier = models.FileField(verbose_name="Fichier", upload_to=get_uuid_path)
    defaut = models.BooleanField(verbose_name="Modèle par défaut", default=False)
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'modeles_word'
        verbose_name = "modèle de document Word"
        verbose_name_plural = "modèles de documents Word"

    def __str__(self):
        return self.nom if self.idmodele else "Nouveau modèle"

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Si le défaut a été supprimé, on le réattribue à une autre objet
        if len(ModeleWord.objects.filter(categorie=self.categorie, defaut=True)) == 0:
            objet = ModeleWord.objects.filter(categorie=self.categorie).first()
            if objet != None:
                objet.defaut = True
                objet.save()


class Sondage(models.Model):
    idsondage = models.AutoField(verbose_name="ID", db_column='IDsondage', primary_key=True)
    titre = models.CharField(verbose_name="Titre", max_length=300)
    description = models.TextField(verbose_name="Description", blank=True, null=True, help_text="Ce texte sera affiché comme introduction du formulaire de saisie.")
    conclusion = models.TextField(verbose_name="Texte après validation", blank=True, null=True, help_text="Ce texte sera affiché après la validation de la réponse par la famille.")
    code = models.CharField(verbose_name="Code du formulaire", max_length=300, default=get_uuid)
    public = models.CharField(verbose_name="Public", max_length=50, choices=[("individu", "Individu"), ("famille", "Famille")], default="famille", help_text="Indiquez si la réponse devra être unique pour la famille ou spécifique à un individu.")
    categories_rattachements = MultiSelectField(verbose_name="Catégories de rattachement", max_length=200, choices=CATEGORIES_RATTACHEMENT, blank=True, null=True, help_text="Sélectionnez les catégories d'individus qui pourront être associés à ce formulaire.")
    modifiable = models.BooleanField(verbose_name="Réponses modifiables", default=True, help_text="Cochez cette case si vous souhaitez que les familles puissent modifier leurs réponses.")
    structure = models.ForeignKey(Structure, verbose_name="Structure", on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'sondages'
        verbose_name = "formulaire"
        verbose_name_plural = "formulaires"

    def __str__(self):
        return self.titre if self.titre else "Nouveau formulaire"


class SondagePage(models.Model):
    idpage = models.AutoField(verbose_name="ID", db_column='IDpage', primary_key=True)
    sondage = models.ForeignKey(Sondage, verbose_name="Formulaire", on_delete=models.CASCADE)
    titre = models.CharField(verbose_name="Titre", max_length=300, help_text="Ce titre sera affiché uniquement si le formulaire comporte plusieurs pages.")
    description = models.TextField(verbose_name="Description", blank=True, null=True, help_text="Ce texte sera affiché sous le titre de la page.")
    ordre = models.IntegerField(verbose_name="Ordre")

    class Meta:
        db_table = 'sondages_pages'
        verbose_name = "page de formulaire"
        verbose_name_plural = "pages de formulaire"

    def __str__(self):
        return self.titre if self.titre else "Nouvelle page de formulaire"

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre
        liste_objects = SondagePage.objects.filter(sondage=self.sondage).order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1


class SondageQuestion(models.Model):
    idquestion = models.AutoField(verbose_name="ID", db_column='IDquestion', primary_key=True)
    page = models.ForeignKey(SondagePage, verbose_name="Page", on_delete=models.CASCADE)
    ordre = models.IntegerField(verbose_name="Ordre")
    label = models.CharField(verbose_name="Label", max_length=250)
    controle = models.CharField(verbose_name="contrôle", max_length=200, choices=[(ctrl["code"], ctrl["label"]) for ctrl in LISTE_CONTROLES_QUESTIONNAIRES])
    choix = models.CharField(verbose_name="Choix", max_length=500, blank=True, null=True, help_text="Saisissez les choix possibles séparés par un point-virgule. Exemple : 'Bananes;Pommes;Poires'")
    texte_aide = models.CharField(verbose_name="Texte d'aide", max_length=500, blank=True, null=True, help_text="Vous pouvez saisir un texte d'aide qui apparaîtra sous le champ de saisie.")
    obligatoire = models.BooleanField(verbose_name="Obligatoire", default=False, help_text="Cochez cette case si la famille doit obligatoirement répondre à cette question.")

    class Meta:
        db_table = 'sondages_questions'
        verbose_name = "question de formulaire"
        verbose_name_plural = "questions de formulaire"

    def __str__(self):
        return self.label

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        # Après la suppression, on rectifie l'ordre
        liste_objects = SondageQuestion.objects.filter(page=self.page).order_by("ordre")
        ordre = 1
        for objet in liste_objects:
            if objet.ordre != ordre:
                objet.ordre = ordre
                objet.save()
            ordre += 1


class SondageRepondant(models.Model):
    idrepondant = models.AutoField(verbose_name="ID", db_column="IDrepondant", primary_key=True)
    sondage = models.ForeignKey(Sondage, verbose_name="Formulaire", on_delete=models.CASCADE)
    famille = models.ForeignKey(Famille, verbose_name="Famille", blank=True, null=True, on_delete=models.CASCADE)
    individu = models.ForeignKey(Individu, verbose_name="Individu", blank=True, null=True, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(verbose_name="Date de création", auto_now_add=True)
    date_modification = models.DateTimeField(verbose_name="Date de modification", blank=True, null=True)

    class Meta:
        db_table = 'sondages_repondants'
        verbose_name = "répondant de formulaire"
        verbose_name_plural = "répondants de formulaire"

    def __str__(self):
        return "Répondant ID%d" % self.idrepondant if self.idrepondant else "Nouveau répondant"


class SondageReponse(models.Model):
    idreponse = models.AutoField(verbose_name="ID", db_column='IDreponse', primary_key=True)
    repondant = models.ForeignKey(SondageRepondant, verbose_name="Répondant", blank=True, null=True, on_delete=models.CASCADE)
    question = models.ForeignKey(SondageQuestion, verbose_name="Question", on_delete=models.CASCADE)
    reponse = models.CharField(verbose_name="Réponse", max_length=450, blank=True, null=True)

    class Meta:
        db_table = 'sondages_reponses'
        verbose_name = "réponse de formulaire"
        verbose_name_plural = "réponses de formulaires"

    def __str__(self):
        return self.reponse

    def Get_reponse_for_ctrl(self):
        if self.question.controle in ("liste_deroulante", "liste_coches"):
            return self.reponse.split(";")
        if self.question.controle in ("entier", "slider"):
            if self.reponse:
                return int(self.reponse)
        if self.question.controle == "case_coche":
            return self.reponse == "True"
        if self.question.controle in ("decimal", "montant"):
            return decimal.Decimal(self.reponse or "0.0")
        return self.reponse

    def Get_reponse_fr(self):
        if not self.reponse:
            return ""
        if self.question.controle in ("liste_deroulante", "liste_coches"):
            return ", ".join(self.reponse.split(";"))
        if self.question.controle in ("entier", "slider") and self.reponse:
            return str(self.reponse)
        if self.question.controle == "case_coche":
            return "oui" if self.reponse == "True" else "non"
        if self.question.controle == "date":
            return utils_dates.ConvertDateToFR(self.reponse)
        if self.question.controle in ("decimal", "montant"):
            return float(decimal.Decimal(self.reponse or 0.0))
        return self.reponse or ""