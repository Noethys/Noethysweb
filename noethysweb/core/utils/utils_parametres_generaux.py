# -*- coding: utf-8 -*-
#  Copyright (c) 2024-2025 Faouzia TEKAYA.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import decimal
from django import forms
from django_summernote.widgets import SummernoteInplaceWidget
from django.template.loader import render_to_string
from core.models import PortailParametre


class Parametre():
    def __init__(self, *args, **kwargs):
        self.code = kwargs.get("code", None)
        self.label = kwargs.get("label", None)
        self.type = kwargs.get("type", None)
        self.valeur = kwargs.get("valeur", None)
        self.help_text = kwargs.get("help_text", None)
        self.required = kwargs.get("required", False)
        self.choix = kwargs.get("choix", [])

    def Get_ctrl(self):
        if self.type == "boolean":
            return forms.BooleanField(label=self.label, required=self.required, help_text=self.help_text)

    def From_db(self, valeur=""):
        if self.type == "boolean":
            self.valeur = valeur == "True"
        else:
            self.valeur = valeur

LISTE_PARAMETRES = [

    # Compte utilisateurs
    Parametre(code="compte_famille", label="Compte Famille", valeur=False, type="boolean", help_text="Cochez cette case pour se connecter sur le portail en tant que Famille."),
    Parametre(code="compte_individu", label="Compte Individu",  valeur=True, type="boolean", help_text="Cochez cette case pour se connecter sur le portail en tant que Individu."),

    # Fiche Individu
    Parametre(code="questionnaire_afficher_page_individu", label="Afficher la page Questionnaire", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Questionnaire sur la fiche Individu."),
    Parametre(code="liens_afficher_page_individu", label="Afficher la page Liens", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Liens sur la fiche Individu."),
    Parametre(code="regimes_alimentaires_afficher_page_individu", label="Afficher la page Régimes alimentaires", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Régimes alimentaires sur la fiche Individu."),
    Parametre(code="maladies_afficher_page_individu", label="Afficher la page Maladies", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Maladies sur la fiche Individu."),
    Parametre(code="medical_afficher_page_individu", label="Afficher la page Médical", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Médical sur la fiche Individu."),
    Parametre(code="assurances_afficher_page_individu", label="Afficher la page Assurances", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Assurances sur la fiche Individu."),
    Parametre(code="contacts_afficher_page_individu", label="Afficher la page Contacts", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Contacts sur la fiche Individu."),
    Parametre(code="transports_afficher_page_individu", label="Afficher la page Transports", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Transports sur la fiche Individu."),
    Parametre(code="consommations_afficher_page_individu", label="Afficher la page Consommations", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Consommations sur la fiche Individu."),

    # Fiche Famille
    Parametre(code="questionnaire_afficher_page_famille", label="Afficher la page Questionnaire", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Questionnaire sur la fiche Famille."),
    Parametre(code="pieces_afficher_page_famille", label="Afficher la page Pièces", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Pièces sur la fiche Famille."),
    Parametre(code="locations_afficher_page_famille", label="Afficher la page Locations", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Locations sur la fiche Famille."),
    Parametre(code="cotisations_afficher_page_famille", label="Afficher la page Adhésions", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Adhésions sur la fiche Famille."),
    Parametre(code="caisse_afficher_page_famille", label="Afficher la page Caisse", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Caisse sur la fiche Famille."),
    Parametre(code="aides_afficher_page_famille", label="Afficher la page Aides", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Aides sur la fiche Famille."),
    Parametre(code="quotients_afficher_page_famille", label="Afficher la page Quotients familiaux", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Quotients familiaux sur la fiche Famille."),
    Parametre(code="prestations_afficher_page_famille", label="Afficher la page Prestations", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Prestations sur la fiche Famille."),
    Parametre(code="factures_afficher_page_famille", label="Afficher la page Factures", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Factures sur la fiche Famille."),
    Parametre(code="reglements_afficher_page_famille", label="Afficher la page Règlements", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Règlements sur la fiche Famille."),
    Parametre(code="messagerie_afficher_page_famille", label="Afficher la page Messagerie", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Questionnaire sur la fiche Famille."),
    Parametre(code="outils_afficher_page_famille", label="Afficher la page Outils", type="boolean",valeur=True, help_text="Cochez cette case pour afficher la page Outils sur la fiche Famille."),
    Parametre(code="consommations_afficher_page_famille", label="Afficher la page Consommations", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Consommations sur la fiche Famille."),

    # Portail Utilisateur
    Parametre(code="outils_afficher_page_portailuser", label="Afficher la page Outils", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Outils sur le menu de Portail Utilisateur."),
    Parametre(code="locations_afficher_page_portailuser", label="Afficher la page Locations", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Locations sur le menu de Portail Utilisateur."),
    Parametre(code="adhesions_afficher_page_portailuser", label="Afficher la page Adhésions", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Adhésions sur le menu de Portail Utilisateur."),
    Parametre(code="consommations_afficher_page", label="Afficher la page Consommations", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Consommations sur le menu de Portail Utilisateur."),
    Parametre(code="factures_afficher_page_portailuser", label="Afficher la page Factures", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Factures sur le menu de Portail Utilisateur."),
    Parametre(code="reglements_afficher_page_portailuser", label="Afficher la page Règlements", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Règlements sur le menu de Portail Utilisateur."),
    Parametre(code="comptabilite_afficher_page_portailuser", label="Afficher la page Comptabilité", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Comptabilité sur le menu de Portail Utilisateur."),
    Parametre(code="collabotrateurs_afficher_page_portailuser", label="Afficher la page Collabotrateurs", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Collabotrateurs sur le menu de Portail Utilisateur."),
    Parametre(code="aides_afficher_page_portailuser", label="Afficher la page Aide", type="boolean", valeur=True, help_text="Cochez cette case pour afficher la page Aide sur le menu de Portail Utilisateur."),

    # Emails par LOT
    Parametre(code="emails_individus_afficher_page", label="Afficher d'envoi des emails par Individus", type="boolean", valeur=False, help_text="Cochez cette case pour afficher la page Individus pour l'envoi des email par lot sur la partie Envoi email par lot."),
    Parametre(code="emails_familles_afficher_page", label="Afficher d'envoi des emails par Familles", type="boolean", valeur=False, help_text="Cochez cette case pour afficher la page Familles pour l'envoi des email par lot sur la partie Envoi email par lot."),
    Parametre(code="emails_activites_afficher_page", label="Afficher d'envoi des emails par Activites",type="boolean", valeur=True,help_text="Cochez cette case pour afficher la page Activites pour l'envoi des email par lot sur la partie Envoi email par lot."),
    Parametre(code="emails_inscriptions_afficher_page", label="Afficher d'envoi des emails par Inscriptions", type="boolean", valeur=False, help_text="Cochez cette case pour afficher la page Insciptions pour l'envoi des email par lot sur la partie Envoi email par lot."),
    Parametre(code="emails_collaborateurs_afficher_page", label="Afficher d'envoi des emails par collaborations", type="boolean", valeur=False, help_text="Cochez cette case pour afficher la page collaborations pour l'envoi des email par lot sur la partie Envoi email par lot."),
    Parametre(code="emails_liste_diffusion_afficher_page", label="Afficher d'envoi des emails par listes de diffusion", type="boolean",valeur=False, help_text="Cochez cette case pour afficher la page Listes de diffusion pour l'envoi des email par lot sur la partie Envoi email par lot."),

]

def Get_dict_parametres():
    """ Renvoi un dict code: valeur des paramètres """
    dict_parametres = {parametre.code: parametre for parametre in LISTE_PARAMETRES}

    for parametre_db in PortailParametre.objects.all():
        if parametre_db.code in dict_parametres:
            dict_parametres[parametre_db.code].From_db(parametre_db.valeur)

    return {code: parametre.valeur for code, parametre in dict_parametres.items()}

def Get_parametre(code=""):
    parametres = Get_dict_parametres()
    return parametres.get(code, None)
