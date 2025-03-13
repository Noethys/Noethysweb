# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


LISTE_ONGLETS = [
    {"code": "resume", "label": "Résumé", "icone": "fa-home", "url": "famille_resume"},
    {"code": "questionnaire", "label": "Questionnaire", "icone": "fa-question", "url": "famille_questionnaire"},
    {"code": "pieces", "label": "Pièces", "icone": "fa-file-text-o", "url": "famille_pieces_liste"},
    {"code": "locations", "label": "Locations", "icone": "fa-shopping-cart", "url": "famille_locations_liste"},
    {"code": "cotisations", "label": "Adhésions", "icone": "fa-folder-o", "url": "famille_cotisations_liste"},
    {"code": "caisse", "label": "Caisse", "icone": "fa-institution ", "url": "famille_caisse"},
    {"code": "aides", "label": "Aides", "icone": "fa-euro", "url": "famille_aides_liste"},
    {"code": "quotients", "label": "Quotients familiaux", "icone": "fa-euro", "url": "famille_quotients_liste"},
    {"code": "prestations", "label": "Prestations", "icone": "fa-euro", "url": "famille_prestations_liste"},
    {"code": "factures", "label": "Factures", "icone": "fa-euro", "url": "famille_factures_liste"},
    {"code": "reglements", "label": "Règlements", "icone": "fa-money", "url": "famille_reglements_liste"},
    {"code": "messagerie", "label": "Messagerie", "icone": "fa-file-text-o", "url": "famille_messagerie_portail"},
    {"code": "portail", "label": "Portail", "icone": "fa-globe", "url": "famille_portail"},
    {"code": "divers", "label": "Paramètres", "icone": "fa-gear", "url": "famille_divers"},
    {"code": "outils", "label": "Outils", "icone": "fa-wrench", "url": "famille_outils"},
    {"code": "consommations", "label": "Consommations", "icone": "fa-calendar", "url": "famille_consommations"},
]
def Get_filtered_onglets():
    from core.utils.utils_parametres_generaux import Get_dict_parametres
    parametres = Get_dict_parametres()

    # Filtrer la liste en fonction des paramètres
    filtered_onglets = [
        onglet for onglet in LISTE_ONGLETS
        if parametres.get(f"{onglet['code']}_afficher_page_famille", True)
    ]
    return filtered_onglets