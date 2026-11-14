# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

# Valeurs proposées par défaut pour le paramétrage des collaborateurs.
# Elles sont importées par le bouton "Importer les valeurs par défaut" des pages de paramétrage
# et par la migration 0237 (uniquement dans les tables vides).
# Les valeurs déjà présentes (même nom, sans tenir compte des majuscules) ne sont jamais modifiées.


TYPES_CONTRATS = [
    "Fonctionnaire titulaire",
    "Fonctionnaire stagiaire",
    "Contractuel CDD",
    "Contractuel CDI",
    "Contrat de projet",
    "Vacataire",
    "CDI",
    "CDD",
    "CDI intermittent",
    "Contrat d'engagement éducatif (CEE)",
    "Apprentissage",
    "Contrat de professionnalisation",
    "Contrat aidé (PEC)",
    "Stage",
    "Service civique",
    "Mise à disposition",
    "Intérim",
]


# type : ADDITION (temps comptabilisé), NEUTRE (temps non comptabilisé), SOUSTRACTION (temps soustrait)
# objectif : NON (selon le type), DUREE (durée planifiée), FORFAIT (durée forfaitaire journalière)
CATEGORIES_EVENEMENTS = [
    {"nom": "Travail", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#3c8dbc"},
    {"nom": "Animation", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#00a65a"},
    {"nom": "Préparation", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#39cccc"},
    {"nom": "Réunion", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#605ca8"},
    {"nom": "Formation", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#3d5a98"},
    {"nom": "Déplacement / mission", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#6c7a89"},
    {"nom": "Télétravail", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#5dade2"},
    {"nom": "Visite médicale", "type": "ADDITION", "objectif": "NON", "chevauchement": False, "couleur": "#95a5a6"},
    {"nom": "Pause", "type": "SOUSTRACTION", "objectif": "NON", "chevauchement": True, "couleur": "#bdc3c7"},
    {"nom": "Astreinte", "type": "NEUTRE", "objectif": "NON", "chevauchement": True, "couleur": "#f39c12"},
    {"nom": "Congés annuels", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#ff851b"},
    {"nom": "RTT", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#f5b041"},
    {"nom": "Jours de fractionnement", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#f8c471"},
    {"nom": "Compte épargne-temps", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#a0522d"},
    {"nom": "Récupération", "type": "NEUTRE", "objectif": "NON", "chevauchement": False, "couleur": "#f1c40f"},
    {"nom": "Maladie", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#dd4b39"},
    {"nom": "Accident du travail", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#a93226"},
    {"nom": "Maternité / paternité", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#d81b60"},
    {"nom": "Enfant malade", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#f1948a"},
    {"nom": "Absence autorisée", "type": "NEUTRE", "objectif": "FORFAIT", "chevauchement": False, "couleur": "#af7ac5"},
    {"nom": "Absence non justifiée", "type": "NEUTRE", "objectif": "NON", "chevauchement": False, "couleur": "#34495e"},
    {"nom": "Grève", "type": "NEUTRE", "objectif": "NON", "chevauchement": False, "couleur": "#555555"},
]


# Chaque type de congé est relié à sa propre catégorie d'évènements (créée si elle n'existe pas)
TYPES_CONGES = [
    {"nom": "Congés annuels", "abrege": "CA", "unite": "JOURS", "categorie": "Congés annuels", "mois_debut": 1, "solde_negatif": True,
     "observations": "Période de référence à adapter : janvier pour l'année civile (fonction publique), juin pour la période de juin à mai (droit privé)."},
    {"nom": "RTT", "abrege": "RTT", "unite": "JOURS", "categorie": "RTT", "mois_debut": 1, "solde_negatif": False, "observations": ""},
    {"nom": "Jours de fractionnement", "abrege": "FR", "unite": "JOURS", "categorie": "Jours de fractionnement", "mois_debut": 1, "solde_negatif": False, "observations": ""},
    {"nom": "Récupération", "abrege": "REC", "unite": "HEURES", "categorie": "Récupération", "mois_debut": 1, "solde_negatif": False, "observations": ""},
    {"nom": "Compte épargne-temps", "abrege": "CET", "unite": "JOURS", "categorie": "Compte épargne-temps", "mois_debut": 1, "solde_negatif": False, "observations": ""},
]


TYPES_QUALIFICATIONS = [
    "BAFA", "BAFA stagiaire", "BAFD", "BAFD stagiaire", "BPJEPS", "DEJEPS", "CPJEPS", "BAPAAT", "BUT / DUT Carrières sociales",
    "CAP AEPE", "Auxiliaire de puériculture", "Éducateur de jeunes enfants", "Infirmier(ère)",
    "PSC1", "SST", "Surveillant de baignade", "BNSSA",
    "Permis B", "Hygiène alimentaire (HACCP)",
]


# duree_validite : None (illimitée) ou "jJ-mM-aA" (jours, mois, années)
# qualification : si renseignée, la pièce est obligatoire uniquement pour les collaborateurs ayant cette qualification
TYPES_PIECES = [
    {"nom": "Pièce d'identité", "duree_validite": None, "qualification": None},
    {"nom": "Attestation de sécurité sociale", "duree_validite": None, "qualification": None},
    {"nom": "RIB", "duree_validite": None, "qualification": None},
    {"nom": "Justificatif de domicile", "duree_validite": None, "qualification": None},
    {"nom": "Extrait de casier judiciaire (B3)", "duree_validite": "j0-m3-a0", "qualification": None},
    {"nom": "Attestation d'honorabilité", "duree_validite": None, "qualification": None},
    {"nom": "Certificat de vaccinations", "duree_validite": None, "qualification": None},
    {"nom": "Diplôme du BAFA", "duree_validite": None, "qualification": "BAFA"},
    {"nom": "Attestation de formation générale BAFA", "duree_validite": None, "qualification": "BAFA stagiaire"},
    {"nom": "Diplôme du BAFD", "duree_validite": None, "qualification": "BAFD"},
    {"nom": "Attestation de formation générale BAFD", "duree_validite": None, "qualification": "BAFD stagiaire"},
    {"nom": "Diplôme du BPJEPS", "duree_validite": None, "qualification": "BPJEPS"},
    {"nom": "Diplôme du DEJEPS", "duree_validite": None, "qualification": "DEJEPS"},
    {"nom": "Diplôme du CPJEPS", "duree_validite": None, "qualification": "CPJEPS"},
    {"nom": "Diplôme du BAPAAT", "duree_validite": None, "qualification": "BAPAAT"},
    {"nom": "Diplôme BUT / DUT Carrières sociales", "duree_validite": None, "qualification": "BUT / DUT Carrières sociales"},
    {"nom": "Diplôme du CAP AEPE", "duree_validite": None, "qualification": "CAP AEPE"},
    {"nom": "Diplôme d'auxiliaire de puériculture", "duree_validite": None, "qualification": "Auxiliaire de puériculture"},
    {"nom": "Diplôme d'éducateur de jeunes enfants", "duree_validite": None, "qualification": "Éducateur de jeunes enfants"},
    {"nom": "Diplôme d'infirmier(ère)", "duree_validite": None, "qualification": "Infirmier(ère)"},
    {"nom": "Certificat PSC1", "duree_validite": None, "qualification": "PSC1"},
    {"nom": "Certificat SST", "duree_validite": "j0-m0-a2", "qualification": "SST"},
    {"nom": "Diplôme de surveillant de baignade", "duree_validite": None, "qualification": "Surveillant de baignade"},
    {"nom": "Carte BNSSA", "duree_validite": None, "qualification": "BNSSA"},
    {"nom": "Permis de conduire", "duree_validite": None, "qualification": "Permis B"},
    {"nom": "Attestation de formation HACCP", "duree_validite": None, "qualification": "Hygiène alimentaire (HACCP)"},
]
