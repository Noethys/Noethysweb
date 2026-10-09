# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Informations complémentaires pour l'affichage des menus (pages sommaires et widget "Mes favoris").

- DESCRIPTIONS_MENUS : sous-titre de chaque page sommaire (clé = code du menu).
- ICONES_RUBRIQUES : icône Font Awesome 4.7 de chaque rubrique (clé = titre de la rubrique).
- COMMANDES : pour chaque commande (clé = code), un tuple (icône Font Awesome 4.7, nature, description).
  La nature détermine la couleur de la tuile :
    "a" = saisir / traiter (bleu)
    "l" = consulter une liste (vert)
    "e" = imprimer / envoyer / exporter (ambre)
    "s" = analyser (violet)

Une commande absente de COMMANDES s'affiche avec son icône d'origine, en bleu et sans description.

- NOUVEAUTES : date de mise en service des nouvelles commandes (clé = code). Un badge "Nouveau" s'affiche
  automatiquement pendant DUREE_NOUVEAUTE jours après cette date.
"""

import datetime

NATURES = {
    "a": "Saisir / traiter",
    "l": "Consulter",
    "e": "Imprimer / envoyer",
    "s": "Analyser",
}


DESCRIPTIONS_MENUS = {
    "parametrage_toc": "Configurer l'organisateur, les activités, les modèles et les données de référence.",
    "outils_toc": "Statistiques, emails, SMS, historique, sauvegardes et maintenance.",
    "individus_toc": "Gérer les familles, les inscriptions et les renseignements.",
    "locations_toc": "Gérer les locations de produits et leur planning.",
    "cotisations_toc": "Suivre les adhésions, leur saisie et leurs dépôts.",
    "consommations_toc": "Saisir, suivre et analyser les présences et les réservations.",
    "facturation_toc": "Générer les factures, les rappels et les attestations, et suivre les prestations.",
    "reglements_toc": "Suivre les paiements reçus, leur ventilation et leurs dépôts.",
    "comptabilite_toc": "Suivre la trésorerie, le budget et les achats.",
    "collaborateurs_toc": "Gérer les collaborateurs, leurs contrats et leurs plannings.",
}


ICONES_RUBRIQUES = {
    "Généralités": "building-o",
    "Activités": "cubes",
    "Adhésions": "id-card-o",
    "Questionnaires": "question-circle-o",
    "Modèles": "clone",
    "Comptabilité": "calculator",
    "Achats": "shopping-basket",
    "Renseignements": "address-book-o",
    "Facturation": "eur",
    "Scolarité": "graduation-cap",
    "Restauration": "cutlery",
    "Notes": "sticky-note-o",
    "Tâches": "check-square-o",
    "Emails": "envelope-o",
    "SMS": "mobile",
    "Calendrier": "calendar",
    "Portail": "globe",
    "Locations": "shopping-cart",
    "Collaborateurs": "users",
    "Transports": "bus",
    "Statistiques": "bar-chart",
    "Historique": "history",
    "Maintenance": "wrench",
    "Sauvegardes": "database",
    "Dépannage": "medkit",
    "Utilitaires": "cogs",
    "Gestion des individus": "users",
    "Inscriptions": "list-alt",
    "Informations": "info-circle",
    "Pièces": "file-o",
    "Formulaires": "check-square-o",
    "Impression": "print",
    "Photos": "camera",
    "Listes de diffusion": "bullhorn",
    "Etat des locations": "list",
    "Gestion des locations": "pencil",
    "Analyse": "bar-chart",
    "Etat des adhésions": "list",
    "Gestion des adhésions": "pencil",
    "Dépôts d'adhésions": "university",
    "Gestion des consommations": "pencil",
    "Listes": "list",
    "Factures": "file-text-o",
    "Rappels": "bell-o",
    "Attestations fiscales": "certificate",
    "Prestations": "shopping-bag",
    "Déductions": "minus-circle",
    "Aides": "life-ring",
    "Impayés": "exclamation-triangle",
    "Tarifs": "tags",
    "Export des écritures comptables": "upload",
    "Règlements": "money",
    "Dépôts de règlements": "university",
    "Divers": "ellipsis-h",
    "Ventilation": "sliders",
    "Opérations": "exchange",
    "Outils": "wrench",
    "Gestion des achats": "shopping-basket",
    "Gestion des collaborateurs": "users",
    "Gestion des contrats": "file-text-o",
    "Gestion des évènements": "calendar",
}


COMMANDES = {

    # ------------------------------------ Paramétrage ------------------------------------

    # Généralités
    "organisateur_modifier": ("building-o", "a", "Nom, coordonnées et logo de l'organisateur."),
    "organisateur_ajouter": ("building-o", "a", "Nom, coordonnées et logo de l'organisateur."),
    "structures_liste": ("sitemap", "a", "Définir les structures et leurs utilisateurs."),

    # Activités
    "types_groupes_activites_liste": ("object-group", "a", "Regrouper les activités pour faciliter les sélections."),
    "activites_liste": ("cubes", "a", "Créer et paramétrer les activités, groupes, unités et tarifs."),

    # Adhésions
    "types_cotisations_liste": ("id-card-o", "a", "Définir les types d'adhésions proposés."),
    "unites_cotisations_liste": ("tags", "a", "Définir les unités et tarifs de chaque type d'adhésion."),

    # Questionnaires
    "questions_liste": ("question-circle-o", "a", "Créer les questions personnalisées des fiches."),

    # Modèles
    "modeles_documents_liste": ("file-text-o", "a", "Mettre en page les factures, attestations et autres documents."),
    "modeles_impressions_liste": ("print", "a", "Enregistrer des réglages d'impression réutilisables."),
    "modeles_word_liste": ("file-word-o", "a", "Gérer les modèles Word pour le publipostage."),
    "modeles_emails_liste": ("envelope-o", "a", "Rédiger les emails types envoyés par l'application."),
    "modeles_sms_liste": ("mobile", "a", "Rédiger les SMS types envoyés par l'application."),
    "modeles_rappels_liste": ("bell-o", "a", "Rédiger les textes des lettres de rappel."),
    "modeles_pes_liste": ("university", "a", "Paramétrer les exports PES vers le Trésor Public."),
    "modeles_prestations_liste": ("shopping-bag", "a", "Prédéfinir des prestations à saisir rapidement."),
    "modeles_prelevements_liste": ("credit-card", "a", "Paramétrer les fichiers de prélèvements SEPA."),
    "modeles_aides_liste": ("life-ring", "a", "Prédéfinir des aides à appliquer aux familles."),

    # Comptabilité
    "comptes_bancaires_liste": ("university", "a", "Déclarer les comptes bancaires de l'organisateur."),
    "modes_reglements_liste": ("money", "a", "Définir les modes de règlement acceptés."),
    "emetteurs_liste": ("bank", "a", "Définir les émetteurs (banques, organismes) des règlements."),
    "postes_analytiques_liste": ("pie-chart", "a", "Définir les postes de la comptabilité analytique."),
    "comptes_comptables_liste": ("book", "a", "Définir le plan de comptes."),
    "categories_comptables_liste": ("folder-o", "a", "Classer les opérations par catégorie comptable."),
    "tiers_liste": ("handshake-o", "a", "Gérer les tiers des opérations comptables."),
    "budgets_liste": ("balance-scale", "a", "Définir les budgets prévisionnels."),
    "releves_bancaires_liste": ("file-text", "a", "Saisir les relevés bancaires pour le rapprochement."),

    # Achats
    "achats_categories_liste": ("tags", "a", "Classer les articles achetés par catégorie."),
    "achats_fournisseurs_liste": ("truck", "a", "Gérer la liste des fournisseurs."),

    # Renseignements
    "types_pieces_liste": ("file-o", "a", "Définir les justificatifs demandés aux familles."),
    "regimes_liste": ("shield", "a", "Définir les régimes sociaux (général, MSA...)."),
    "caisses_liste": ("building", "a", "Définir les caisses d'allocations."),
    "types_quotients_liste": ("percent", "a", "Définir les types de quotients familiaux."),
    "api_particulier_parametrer": ("plug", "a", "Configurer l'accès à l'API Particulier."),
    "categories_travail_liste": ("briefcase", "a", "Définir les catégories socio-professionnelles."),
    "secteurs_liste": ("map-marker", "a", "Définir les secteurs géographiques."),
    "types_sieste_liste": ("bed", "a", "Définir les types de sieste."),
    "types_regimes_alimentaires_liste": ("cutlery", "a", "Définir les régimes alimentaires (sans porc, végétarien...)."),
    "categories_informations_liste": ("info-circle", "a", "Classer les informations personnelles des individus."),
    "types_maladies_liste": ("heartbeat", "a", "Définir les maladies suivies dans les fiches."),
    "types_vaccins_liste": ("eyedropper", "a", "Définir les vaccins et leur validité."),
    "medecins_liste": ("user-md", "a", "Gérer l'annuaire des médecins."),
    "assureurs_liste": ("umbrella", "a", "Gérer la liste des assureurs."),

    # Facturation
    "lots_factures_liste": ("files-o", "a", "Définir les lots pour regrouper les factures."),
    "prefixes_factures_liste": ("hashtag", "a", "Définir les préfixes de numérotation des factures."),
    "messages_factures_liste": ("commenting-o", "a", "Rédiger les messages imprimés sur les factures."),
    "regies_liste": ("bank", "a", "Définir les régies et leurs coordonnées."),
    "perceptions_liste": ("university", "a", "Définir les trésoreries et perceptions."),

    # Scolarité
    "niveaux_scolaires_liste": ("signal", "a", "Définir les niveaux scolaires (PS, CP...)."),
    "ecoles_liste": ("graduation-cap", "a", "Gérer la liste des écoles."),
    "classes_liste": ("users", "a", "Définir les classes de chaque école."),

    # Restauration
    "restaurateurs_liste": ("cutlery", "a", "Gérer les restaurateurs et leurs menus."),
    "menus_categories_liste": ("list", "a", "Définir les catégories de plats des menus."),
    "menus_legendes_liste": ("tag", "a", "Définir les légendes (bio, local...) des menus."),
    "modeles_commandes_liste": ("clipboard", "a", "Définir les modèles de commandes de repas."),
    "modeles_commandes_colonnes_liste": ("columns", "a", "Définir les colonnes des modèles de commandes."),

    # Notes
    "notes_categories_liste": ("sticky-note-o", "a", "Classer les notes par catégorie."),

    # Tâches
    "taches_recurrentes_liste": ("repeat", "a", "Programmer des tâches qui reviennent régulièrement."),

    # Emails
    "adresses_mail_liste": ("at", "a", "Configurer les adresses et serveurs d'envoi d'emails."),
    "signatures_emails_liste": ("pencil-square-o", "a", "Rédiger les signatures des emails."),
    "listes_diffusion_liste": ("bullhorn", "a", "Créer les listes de diffusion."),

    # SMS
    "configurations_sms_liste": ("mobile", "a", "Configurer le service d'envoi de SMS."),

    # Calendrier
    "vacances_liste": ("sun-o", "a", "Saisir les périodes de vacances scolaires."),
    "feries_fixes_liste": ("calendar-o", "a", "Définir les jours fériés à date fixe."),
    "feries_variables_liste": ("calendar-o", "a", "Saisir les jours fériés variables (Pâques...)."),

    # Portail
    "portail_parametres_modifier": ("globe", "a", "Régler l'apparence et les fonctions du portail famille."),
    "portail_parametres_renseignements_modifier": ("address-card-o", "a", "Choisir les renseignements modifiables par les familles."),
    "categories_compte_internet_liste": ("key", "a", "Définir les catégories de comptes internet."),
    "types_consentements_liste": ("check-square-o", "a", "Définir les consentements à faire accepter."),
    "unites_consentements_liste": ("check", "a", "Gérer les versions des consentements."),
    "albums_liste": ("picture-o", "a", "Publier des albums photos sur le portail."),
    "sondages_liste": ("check-square-o", "a", "Créer des formulaires à remplir sur le portail."),
    "images_articles_liste": ("image", "a", "Gérer les images utilisées dans les articles."),
    "articles_liste": ("newspaper-o", "a", "Publier des actualités sur le portail."),
    "images_fond_liste": ("image", "a", "Gérer les images de fond du portail."),
    "portail_documents_liste": ("download", "a", "Proposer des documents à télécharger."),

    # Locations
    "categories_produits_liste": ("tags", "a", "Classer les produits à louer par catégorie."),
    "produits_liste": ("cube", "a", "Gérer les produits proposés à la location."),

    # Collaborateurs
    "types_qualifications_collaborateurs_liste": ("certificate", "a", "Définir les qualifications (BAFA, PSC1...)."),
    "types_pieces_collaborateurs_liste": ("file-o", "a", "Définir les pièces demandées aux collaborateurs."),
    "types_evenements_collaborateurs_liste": ("calendar-check-o", "a", "Définir les catégories d'évènements du planning."),
    "types_postes_collaborateurs_liste": ("briefcase", "a", "Définir les postes occupés par les collaborateurs."),
    "modeles_plannings_collaborateurs_liste": ("calendar", "a", "Créer des plannings types réutilisables."),
    "groupes_collaborateurs_liste": ("users", "a", "Regrouper les collaborateurs."),

    # Transports
    "parametrage_transports": ("bus", "a", "Définir compagnies, lignes, arrêts et lieux."),

    # ------------------------------------ Outils ------------------------------------

    # Statistiques
    "statistiques": ("bar-chart", "s", "Statistiques sur les individus, familles, consommations et finances."),
    "statistiques_portail": ("line-chart", "s", "Mesurer l'utilisation du portail famille."),

    # Emails
    "contacts_liste": ("address-book-o", "a", "Gérer les carnets d'adresses."),
    "editeur_emails": ("envelope-o", "e", "Rédiger et envoyer un email à plusieurs destinataires."),
    "emails_liste": ("inbox", "l", "Consulter les emails envoyés."),

    # SMS
    "editeur_sms": ("mobile", "e", "Rédiger et envoyer un SMS à plusieurs destinataires."),
    "sms_liste": ("comments-o", "l", "Consulter les SMS envoyés."),

    # Historique
    "historique": ("history", "l", "Retrouver les actions effectuées par les utilisateurs."),
    "notes_liste": ("sticky-note-o", "l", "Consulter toutes les notes."),
    "taches_liste": ("check-square-o", "l", "Consulter et cocher les tâches."),

    # Maintenance
    "update": ("cloud-download", "a", "Installer la dernière version de l'application."),
    "notes_versions": ("file-text-o", "l", "Découvrir les nouveautés de chaque version."),
    "utilisateurs_bloques_liste": ("lock", "a", "Débloquer les comptes après trop d'échecs de connexion."),

    # Calendrier
    "calendrier_annuel": ("calendar", "l", "Voir l'année avec vacances et jours fériés."),

    # Sauvegardes
    "sauvegarde_creer": ("database", "a", "Créer une sauvegarde des données."),
    "desk_creer": ("download", "e", "Récupérer les données pour une utilisation hors ligne."),

    # Restauration
    "commandes_liste": ("cutlery", "a", "Préparer et envoyer les commandes de repas."),

    # Portail
    "messagerie_portail": ("envelope", "a", "Répondre aux messages reçus des familles."),
    "messages_portail_liste": ("comments-o", "l", "Consulter tous les messages du portail."),
    "demandes_portail_liste": ("history", "l", "Retrouver les modifications faites par les familles."),
    "suivi_reservations": ("tachometer", "s", "Suivre les réservations faites sur le portail."),

    # Dépannage
    "correcteur": ("medkit", "a", "Détecter et corriger les anomalies des données."),
    "liste_conso_sans_presta": ("chain-broken", "l", "Repérer les consommations sans prestation associée."),

    # Utilitaires
    "procedures": ("terminal", "a", "Lancer des procédures techniques de maintenance."),

    # ------------------------------------ Individus ------------------------------------

    # Gestion des individus
    "famille_liste": ("users", "l", "Rechercher une famille et ouvrir sa fiche."),
    "individu_liste": ("user", "l", "Lister tous les individus et leur famille."),
    "individus_detaches_liste": ("user-times", "l", "Retrouver les individus sans famille."),
    "individus_doublons_liste": ("clone", "a", "Repérer et fusionner les fiches en double."),
    "individus_recherche_avancee": ("search-plus", "l", "Croiser plusieurs critères de recherche."),
    "effacer_familles": ("eraser", "a", "Supprimer les données des familles parties (RGPD)."),
    "importer_individus": ("upload", "a", "Créer des fiches depuis un fichier tableur."),

    # Inscriptions
    "inscriptions_liste": ("list-alt", "l", "Consulter toutes les inscriptions aux activités."),
    "liste_inscriptions_attente": ("hourglass-half", "l", "Valider ou refuser les demandes d'inscription."),
    "liste_inscriptions_refus": ("ban", "l", "Retrouver les inscriptions refusées."),
    "inscriptions_activite_liste": ("cubes", "l", "Lister les inscrits d'une activité donnée."),
    "liste_familles_sans_inscriptions": ("user-o", "l", "Repérer les familles sans aucune inscription."),
    "imprimer_liste_inscrits": ("print", "e", "Éditer la liste des inscrits d'une activité."),
    "suivi_inscriptions": ("tachometer", "s", "Voir le remplissage des activités et des groupes."),
    "inscriptions_impression": ("file-pdf-o", "e", "Imprimer les confirmations d'inscription."),
    "inscriptions_email": ("envelope-o", "e", "Envoyer les confirmations d'inscription."),
    "inscriptions_saisir_lot": ("clone", "a", "Inscrire plusieurs individus en une fois."),
    "inscriptions_modifier": ("pencil-square-o", "a", "Modifier plusieurs inscriptions en une fois."),
    "inscriptions_changer_groupe": ("exchange", "a", "Déplacer plusieurs inscrits vers un autre groupe."),

    # Scolarité
    "inscriptions_scolaires_liste": ("graduation-cap", "a", "Affecter les élèves aux écoles et classes."),
    "scolarites_liste": ("road", "l", "Consulter le parcours scolaire des individus."),

    # Informations
    "edition_renseignements": ("file-text", "e", "Imprimer les fiches de renseignements en PDF."),
    "liste_anniversaires": ("birthday-cake", "e", "Imprimer la liste des anniversaires."),
    "liste_regimes_caisses": ("shield", "l", "Lister le régime et la caisse de chaque famille."),
    "liste_quotients": ("percent", "l", "Lister les quotients familiaux et revenus."),
    "importer_quotients": ("cloud-download", "a", "Récupérer les quotients via l'API Particulier."),
    "liste_codes_comptables": ("barcode", "l", "Lister les codes comptables des familles."),
    "liste_titulaires_helios": ("university", "l", "Contrôler les titulaires Hélios des familles."),
    "mandats_liste": ("credit-card", "l", "Gérer les mandats de prélèvement SEPA."),
    "contacts_urgence_liste": ("phone", "l", "Lister les personnes à prévenir et autorisées."),
    "edition_contacts": ("address-book-o", "e", "Imprimer les coordonnées des familles."),
    "regimes_alimentaires_liste": ("cutlery", "l", "Lister les régimes alimentaires des individus."),
    "maladies_liste": ("heartbeat", "l", "Lister les maladies déclarées."),
    "informations_liste": ("info-circle", "l", "Lister les informations personnelles et médicales."),
    "liste_vaccinations_manquantes": ("eyedropper", "l", "Repérer les vaccins manquants ou périmés."),
    "liste_assurances": ("umbrella", "l", "Lister les assurances des individus."),
    "edition_informations": ("print", "e", "Imprimer les informations personnelles."),
    "liste_comptes_internet": ("key", "l", "Gérer les comptes d'accès au portail."),
    "mails_liste": ("at", "l", "Lister les adresses email des familles."),
    "certifications_individus": ("check-circle-o", "l", "Voir les fiches certifiées par les familles."),

    # Pièces
    "liste_pieces_manquantes": ("exclamation-circle", "l", "Lister les justificatifs non fournis par famille."),
    "liste_pieces_fournies": ("check-circle", "l", "Contrôler les pièces reçues et leur validité."),

    # Questionnaires
    "questionnaires_familles_liste": ("question-circle-o", "l", "Consulter les réponses aux questions familiales."),
    "questionnaires_individus_liste": ("question-circle", "l", "Consulter les réponses aux questions individuelles."),

    # Formulaires
    "sondages_reponses_resume": ("check-square-o", "s", "Consulter les réponses aux formulaires du portail."),

    # Impression
    "etiquettes_individus": ("id-badge", "e", "Imprimer étiquettes, badges et cartes."),

    # Photos
    "liste_photos_manquantes": ("camera", "l", "Repérer les individus sans photo."),
    "importation_photos": ("upload", "a", "Associer un lot de photos aux fiches."),

    # Transports
    "progtransports_liste": ("calendar", "a", "Programmer les transports réguliers."),
    "transports_liste": ("bus", "l", "Lister les transports des individus."),
    "etat_transports": ("print", "e", "Imprimer le récapitulatif des transports."),

    # Listes de diffusion
    "abonnes_listes_diffusion_liste": ("bullhorn", "a", "Inscrire ou désinscrire des abonnés."),

    # ------------------------------------ Locations ------------------------------------

    "locations_liste": ("list", "l", "Consulter toutes les locations."),
    "locations_impression": ("print", "e", "Imprimer des confirmations de location."),
    "locations_email": ("envelope-o", "e", "Envoyer des confirmations de location."),
    "planning_locations": ("calendar", "a", "Voir et saisir les locations sur un planning."),
    "synthese_locations": ("pie-chart", "s", "Totaliser les locations par produit et période."),

    # ------------------------------------ Adhésions ------------------------------------

    "cotisations_liste": ("list", "l", "Consulter toutes les adhésions."),
    "cotisations_impression": ("print", "e", "Imprimer des cartes ou reçus d'adhésion."),
    "cotisations_email": ("envelope-o", "e", "Envoyer des adhésions par email."),
    "liste_cotisations_manquantes": ("exclamation-circle", "l", "Repérer les familles sans adhésion à jour."),
    "liste_adherents": ("users", "l", "Lister les adhérents d'une période."),
    "saisie_lot_cotisations": ("clone", "a", "Créer des adhésions pour plusieurs familles."),
    "liste_cotisations_disponibles": ("clock-o", "l", "Lister les adhésions restant à déposer."),
    "depots_cotisations_liste": ("university", "a", "Créer et consulter les dépôts d'adhésions."),
    "statistiques_cotisations": ("bar-chart", "s", "Tableau de bord des adhésions."),

    # ------------------------------------ Consommations ------------------------------------

    # Gestion des consommations
    "edition_liste_conso": ("print", "e", "Imprimer la liste des présents par date, activité et groupe."),
    "gestionnaire_conso": ("table", "a", "Saisir les présences de plusieurs individus sur une grille."),
    "pointeuse_conso": ("clock-o", "a", "Pointer les arrivées et départs au fil de la journée."),
    "suivi_consommations": ("tachometer", "s", "Visualiser le remplissage des activités par date."),
    "consommations_traitement_lot": ("clone", "a", "Ajouter ou supprimer des consommations en masse."),
    "suivi_pointage": ("check-square-o", "l", "Repérer les consommations non pointées."),

    # Listes
    "liste_consommations": ("list", "l", "Rechercher et filtrer toutes les consommations saisies."),
    "liste_attente": ("hourglass-half", "l", "Consulter et réattribuer les places en attente."),
    "liste_refus": ("ban", "l", "Retrouver les demandes refusées faute de place."),
    "liste_absences": ("user-times", "l", "Lister les absences justifiées ou non."),
    "liste_demandes": ("inbox", "l", "Traiter les demandes de réservation du portail."),
    "liste_repas": ("cutlery", "l", "Compter les repas à commander par jour."),
    "liste_durees": ("clock-o", "l", "Calculer les durées de présence par individu."),

    # Analyse
    "etat_global": ("calculator", "s", "Calculer les heures et journées réalisées par période."),
    "frequentation_caf": ("building", "s", "Obtenir pas à pas les chiffres à déclarer à la CAF."),
    "etat_nomin": ("id-card-o", "s", "Détailler la fréquentation individu par individu."),
    "synthese_consommations": ("pie-chart", "s", "Totaliser les consommations par activité et période."),
    "statistiques_consommations": ("bar-chart", "s", "Tableau de bord de la fréquentation."),
    "evolution_reservations": ("line-chart", "s", "Suivre l'évolution des réservations dans le temps."),
    "analyse_ia_frequentation": ("magic", "s", "Obtenir un commentaire automatique des tendances."),

    # ------------------------------------ Facturation ------------------------------------

    # Factures
    "factures_generation": ("cogs", "a", "Créer les factures d'une période."),
    "lots_pes_liste": ("university", "e", "Exporter les factures vers le Trésor Public (PES)."),
    "lots_prelevements_liste": ("credit-card", "e", "Préparer les fichiers de prélèvements SEPA."),
    "factures_impression": ("print", "e", "Imprimer les factures en PDF."),
    "factures_email": ("envelope-o", "e", "Envoyer les factures par email."),
    "liste_factures": ("list", "l", "Rechercher, consulter et annuler des factures."),
    "liste_factures_detaillees": ("list-ul", "l", "Voir le détail des prestations de chaque facture."),
    "edition_recap_factures": ("file-pdf-o", "e", "Imprimer un récapitulatif d'un lot de factures."),
    "factures_modifier": ("pencil-square-o", "a", "Modifier plusieurs factures en une fois."),

    # Rappels
    "rappels_generation": ("cogs", "a", "Créer les lettres de rappel des impayés."),
    "liste_rappels": ("list", "l", "Consulter les lettres de rappel."),
    "rappels_impression": ("print", "e", "Imprimer les lettres de rappel."),
    "rappels_email": ("envelope-o", "e", "Envoyer les lettres de rappel par email."),

    # Attestations fiscales
    "attestations_fiscales_generation": ("cogs", "a", "Créer les attestations pour la déclaration d'impôts."),
    "liste_attestations_fiscales": ("list", "l", "Consulter les attestations fiscales."),
    "attestations_fiscales_impression": ("print", "e", "Imprimer les attestations fiscales."),
    "attestations_fiscales_email": ("envelope-o", "e", "Envoyer les attestations fiscales par email."),

    # Prestations
    "liste_prestations": ("list", "l", "Rechercher et filtrer les prestations."),
    "liste_soldes": ("balance-scale", "l", "Consulter le solde de chaque famille."),
    "synthese_prestations": ("pie-chart", "s", "Totaliser les prestations par activité et période."),
    "statistiques_prestations": ("bar-chart", "s", "Tableau de bord des prestations."),
    "edition_prestations": ("print", "e", "Imprimer la liste des prestations."),
    "recalculer_prestations": ("refresh", "a", "Recalculer les prestations après un changement de tarif."),
    "saisie_lot_forfaits_credits": ("clone", "a", "Attribuer un forfait-crédit à plusieurs individus."),

    # Déductions
    "liste_deductions": ("list", "l", "Consulter les déductions appliquées."),
    "synthese_deductions": ("pie-chart", "s", "Totaliser les déductions par type et période."),

    # Aides
    "aides_liste": ("life-ring", "l", "Consulter les aides attribuées aux familles."),

    # Impayés
    "synthese_impayes": ("exclamation-triangle", "s", "Analyser les impayés par famille et période."),
    "solder_impayes": ("check", "a", "Solder les petits impayés en une fois."),

    # Tarifs
    "liste_tarifs": ("tags", "l", "Consulter les tarifs de toutes les activités."),

    # Export des écritures comptables
    "export_ecritures_ebp": ("upload", "e", "Exporter les écritures vers EBP Compta."),
    "export_ecritures_cloe": ("upload", "e", "Exporter les écritures vers Cloé."),
    "export_ecritures_cwe": ("upload", "e", "Exporter les écritures vers Comptabilité Web Entreprise."),
    "export_ecritures_quadra": ("upload", "e", "Exporter les écritures vers Quadra Compta."),
    "export_ecritures_sage": ("upload", "e", "Exporter les écritures vers Sage."),

    # ------------------------------------ Règlements ------------------------------------

    "liste_reglements": ("list", "l", "Rechercher un règlement et ouvrir sa fiche."),
    "liste_detaillee_reglements": ("list-ul", "l", "Voir chaque règlement avec son payeur et sa ventilation."),
    "detail_ventilations_reglements": ("random", "l", "Savoir quelles prestations chaque règlement a payées."),
    "edition_ventilations_reglements": ("print", "e", "Imprimer la ventilation des règlements par période."),
    "reglements_lot_factures": ("files-o", "l", "Lister les paiements reçus pour un lot de factures."),
    "synthese_modes_reglements": ("pie-chart", "s", "Totaliser les encaissements par mode de paiement."),
    "statistiques_reglements": ("bar-chart", "s", "Tableau de bord des encaissements, dépôts et délais de paiement."),
    "liste_reglements_disponibles": ("clock-o", "l", "Lister les chèques et espèces restant à déposer."),
    "detail_prestations_depot": ("shopping-bag", "l", "Voir les prestations réglées par un dépôt."),
    "detail_ventilations_depots": ("random", "l", "Ventiler un dépôt par activité ou par poste."),
    "depots_reglements_liste": ("university", "a", "Créer un bordereau de dépôt en banque."),
    "liste_recus": ("file-text-o", "l", "Retrouver les reçus déjà édités."),
    "liste_paiements": ("credit-card", "l", "Suivre les paiements en ligne (PayFIP, Payzen, HelloAsso)."),
    "corriger_ventilation": ("wrench", "a", "Repérer et corriger les règlements mal ventilés."),

    # ------------------------------------ Comptabilité ------------------------------------

    "comptabilite_liste_comptes": ("university", "l", "Consulter les comptes et leur solde."),
    "operations_tresorerie_liste": ("exchange", "a", "Saisir les recettes et dépenses de trésorerie."),
    "operations_budgetaires_liste": ("balance-scale", "a", "Saisir les opérations budgétaires."),
    "virements_liste": ("arrows-h", "a", "Saisir les virements entre comptes."),
    "suivi_tresorerie": ("line-chart", "s", "Suivre l'évolution de la trésorerie."),
    "suivi_budget": ("tasks", "s", "Comparer le réalisé au budget prévisionnel."),
    "rapprochements_liste": ("check-square-o", "a", "Pointer les opérations sur les relevés bancaires."),
    "achats_demandes_liste": ("shopping-cart", "a", "Saisir et suivre les demandes d'achats."),
    "achats_articles_liste": ("cube", "l", "Consulter les articles à acheter."),
    "edition_liste_achats": ("print", "e", "Imprimer une liste d'achats."),
    "suivi_achats": ("tachometer", "s", "Suivre l'avancement des achats."),
    "planning_achats": ("calendar", "l", "Voir les achats sur un planning."),

    # ------------------------------------ Collaborateurs ------------------------------------

    "collaborateur_liste": ("users", "l", "Rechercher un collaborateur et ouvrir sa fiche."),
    "importer_collaborateurs": ("upload", "a", "Créer des fiches depuis un fichier tableur."),
    "contrats_liste": ("file-text-o", "l", "Consulter les contrats des collaborateurs."),
    "fusionner_contrats_word": ("file-word-o", "e", "Générer les contrats à partir d'un modèle Word."),
    "appliquer_modele_planning": ("calendar-plus-o", "a", "Appliquer un planning type à des collaborateurs."),
    "planning_collaborateurs": ("calendar", "a", "Voir et saisir les évènements sur un planning."),
}


DUREE_NOUVEAUTE = 31

NOUVEAUTES = {
    "export_ecritures_sage": "2026-09-07",
    "etat_transports": "2026-09-10",
    "liste_assurances": "2026-09-13",
    "liste_adherents": "2026-09-18",
    "statistiques_cotisations": "2026-10-04",
    "statistiques_consommations": "2026-10-04",
    "statistiques_prestations": "2026-10-04",
    "frequentation_caf": "2026-10-09",
    "statistiques_reglements": "2026-10-09",
}


def Est_nouveau(code=""):
    """ Indique si la commande a été mise en service il y a moins de DUREE_NOUVEAUTE jours """
    if code not in NOUVEAUTES:
        return False
    try:
        date_ajout = datetime.date.fromisoformat(NOUVEAUTES[code])
    except ValueError:
        return False
    return 0 <= (datetime.date.today() - date_ajout).days < DUREE_NOUVEAUTE


def Get_infos_commande(code="", icone_defaut="file-text-o"):
    """ Renvoie (icône, nature, description) d'une commande """
    return COMMANDES.get(code, (icone_defaut, "a", ""))
