# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

LISTE_ONGLETS = [
    {"code": "resume", "label": "Résumé", "icone": "fa-home", "url": "individu_resume"},
    {"code": "identite", "label": "Identité", "icone": "fa-user", "url": "individu_identite"},
    {"code": "questionnaire", "label": "Questionnaire", "icone": "fa-question", "url": "individu_questionnaire"},
    {"code": "liens", "label": "Liens", "icone": "fa-link", "url": "individu_liens"},
    {"code": "coords", "label": "Coordonnées", "icone": "fa-map-marker", "url": "individu_coords"},
    {"code": "scolarite", "label": "Scolarité", "icone": "fa-graduation-cap", "url": "individu_scolarite_liste"},
    {"code": "inscriptions", "label": "Inscriptions", "icone": "fa-ticket", "url": "individu_inscriptions_liste"},
    {"code": "regimes_alimentaires", "label": "Régimes alimentaires", "icone": "fa-cutlery", "url": "individu_regimes_alimentaires"},
    {"code": "maladies", "label": "Maladies", "icone": "fa-stethoscope", "url": "individu_maladies"},
    {"code": "medical", "label": "Médical", "icone": "fa-heartbeat", "url": "individu_medical_liste"},
    {"code": "assurances", "label": "Assurances", "icone": "fa-shield", "url": "individu_assurances_liste"},
    {"code": "contacts", "label": "Contacts", "icone": "fa-users", "url": "individu_contacts_liste"},
    {"code": "transports", "label": "Transports", "icone": "fa-bus", "url": "individu_transports_liste"},
    {"code": "consommations", "label": "Consommations", "icone": "fa-calendar", "url": "famille_consommations"},
]

def Get_filtered_onglets():
    from core.utils.utils_parametres_generaux import Get_dict_parametres
    parametres = Get_dict_parametres()

    # Filtrer la liste en fonction des paramètres
    filtered_onglets = [
        onglet for onglet in LISTE_ONGLETS
        if parametres.get(f"{onglet['code']}_afficher_page_individu", True)
    ]
    return filtered_onglets
