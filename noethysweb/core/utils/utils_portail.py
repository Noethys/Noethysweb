# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.models import PortailParametre, AdresseMail, ImageFond
from django_summernote.widgets import SummernoteInplaceWidget
from django.template.loader import render_to_string


class Parametre():
    def __init__(self, *args, **kwargs):
        self.code = kwargs.get("code", None)
        self.label = kwargs.get("label", None)
        self.type = kwargs.get("type", None)
        self.valeur = kwargs.get("valeur", None)
        self.help_text = kwargs.get("help_text", None)
        self.required = kwargs.get("required", False)

    def Get_ctrl(self):
        if self.type == "boolean":
            return forms.BooleanField(label=self.label, required=self.required, help_text=self.help_text)
        if self.type == "char_1ligne":
            return forms.CharField(label=self.label, required=self.required, help_text=self.help_text)
        if self.type == "char_2lignes":
            return forms.CharField(label=self.label, required=self.required, help_text=self.help_text, widget=forms.Textarea(attrs={'rows': 2}))
        if self.type == "adresse_exp":
            return forms.ChoiceField(label=self.label, choices=[(None, "Aucune")] + [(adresse_exp.pk, adresse_exp.adresse) for adresse_exp in AdresseMail.objects.all().order_by("adresse")], required=self.required, help_text=self.help_text)
        if self.type == "image_fond":
            return forms.ChoiceField(label=self.label, choices=[(None, "Image par défaut")] + [(image.pk, image.titre) for image in ImageFond.objects.all().order_by("titre")], required=self.required, help_text=self.help_text)
        if self.type == "html":
            return forms.CharField(label=self.label, required=self.required, help_text=self.help_text, widget=SummernoteInplaceWidget(
                attrs={'summernote': {'width': '100%', 'height': '200px', 'toolbar': [
                    # ['style', ['style']],
                    ['font', ['bold', 'underline', 'clear']],
                    # ['fontname', ['fontname']],
                    ['color', ['color']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['table', ['table']],
                    # ['insert', ['link', 'picture', 'video']],
                    ['view', ['fullscreen', 'codeview', 'help']],
                ]}}))

    def From_db(self, valeur=""):
        if self.type == "boolean":
            self.valeur = valeur == "True"
        else:
            self.valeur = valeur




LISTE_PARAMETRES = [
    # Connexion
    Parametre(code="connexion_image_fond", label="Image de fond", type="image_fond", valeur=None, help_text="Sélectionnez une image de fond dans la liste. Vous pouvez ajouter de nouvelles images depuis le menu Paramétrage > Images de fond."),
    Parametre(code="connexion_adresse_exp", label="Adresse d'expédition", type="adresse_exp", valeur=None, help_text="Cette adresse mail est utilisée pour envoyer des mails de réinitialisation de mots de passe. A défaut de sélection, la fonction mot de passe oublié sera désactivée."),

    # Accueil
    Parametre(code="accueil_texte_bienvenue", label="Texte de bienvenue", type="html", valeur="Bienvenue sur le portail Famille"),
    Parametre(code="accueil_url_video", label="URL vidéo", type="char_1ligne", valeur="", help_text="Saisissez l'URL d'un tutoriel vidéo que vous souhaitez voir apparaître sur la page d'accueil."),
    Parametre(code="accueil_titre_video", label="Titre de la vidéo", type="char_1ligne", valeur="Découvrez le portail en vidéo", help_text="Saisissez le titre qui apparaîtra dans le bouton de lecture de la vidéo."),

    # Renseignements
    Parametre(code="renseignements_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="renseignements_intro", label="Texte d'introduction", type="char_2lignes", valeur="Cliquez sur l'une des fiches listées ci-dessous pour consulter les renseignements et les corriger si besoin."),
    Parametre(code="validation_auto:famille_caisse", label="Validation automatique de la page 'Caisse'", type="boolean", valeur=True),
    Parametre(code="validation_auto:individu_identite", label="Validation automatique de la page 'Identité'", type="boolean", valeur=True),
    Parametre(code="validation_auto:individu_coords", label="Validation automatique de la page 'Coordonnées'", type="boolean", valeur=True),
    Parametre(code="validation_auto:individu_regimes_alimentaires", label="Validation automatique de la page 'Régimes alimentaires'", type="boolean", valeur=True),
    Parametre(code="validation_auto:individu_maladies", label="Validation automatique de la page 'Maladies'", type="boolean", valeur=True),
    Parametre(code="validation_auto:individu_medecin", label="Validation automatique de la page 'Médecin'", type="boolean", valeur=True),

    # Documents
    Parametre(code="documents_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="documents_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez ici consulter ou transmettre des documents."),

    # Réservations
    Parametre(code="reservations_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="reservations_intro", label="Texte d'introduction", type="char_2lignes", valeur="Sélectionnez une activité puis cliquez sur une des périodes disponibles pour accéder au calendrier des réservations correspondant."),
    Parametre(code="reservations_intro_planning", label="Texte d'introduction du planning", type="char_2lignes", valeur="Cliquez dans les cases pour ajouter ou supprimer des consommations avant de valider l'envoi des données."),

    # Facturation
    Parametre(code="facturation_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="facturation_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez consulter ici les données de facturation."),
    Parametre(code="facturation_afficher_numero_facture", label="Afficher le numéro des factures", type="boolean", valeur=True),
    Parametre(code="facturation_afficher_solde_facture", label="Afficher le solde actuel des factures", type="boolean", valeur=True),
    Parametre(code="facturation_autoriser_detail_facture", label="Afficher le détail des factures", type="boolean", valeur=True),
    Parametre(code="facturation_autoriser_telechargement_facture", label="Autoriser le téléchargement des factures", type="boolean", valeur=True),

    # Règlements
    Parametre(code="reglements_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="reglements_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez consulter ici la liste de vos règlements."),
    Parametre(code="reglements_afficher_encaissement", label="Afficher la date d'encaissement", type="boolean", valeur=True),
    Parametre(code="reglements_autoriser_telechargement_recu", label="Autoriser le téléchargement du reçu", type="boolean", valeur=True),

    # Contact
    Parametre(code="contact_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="contact_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez trouver ici les moyens de correspondre avec l'organisateur."),
    Parametre(code="messagerie_intro", label="Texte d'introduction de la messagerie", type="char_2lignes", valeur="Saisissez un message et cliquez sur le bouton Envoyer."),

    # Mentions
    Parametre(code="mentions_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="mentions_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez consulter ici les mentions légales du portail."),
    Parametre(code="mentions_conditions_generales", label="Conditions générales d'utilisation", type="html", valeur=render_to_string("portail/modele_conditions_generales.html"), help_text="Vous pouvez insérer dans le texte les mots-clés suivants : {ORGANISATEUR_NOM},  {ORGANISATEUR_RUE}, {ORGANISATEUR_CP}, {ORGANISATEUR_VILLE}."),

]


def Get_dict_parametres():
    """ Renvoi un dict code: valeur des paramètres """
    dict_parametres = {parametre.code: parametre for parametre in LISTE_PARAMETRES}
    for parametre_db in PortailParametre.objects.all():
        dict_parametres[parametre_db.code].From_db(parametre_db.valeur)
    return {code: parametre.valeur for code, parametre in dict_parametres.items()}

def Get_parametre(code=""):
    parametres = Get_dict_parametres()
    return parametres.get(code, None)
