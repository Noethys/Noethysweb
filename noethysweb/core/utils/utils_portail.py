# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import decimal
from django import forms
from core.models import PortailParametre, AdresseMail, ImageFond, ModeReglement, CompteBancaire, ModeleImpression
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
        self.choix = kwargs.get("choix", [])

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
        if self.type == "comptes_bancaires":
            return forms.ChoiceField(label=self.label, choices=[(None, "Aucun")] + [(compte.pk, compte.nom) for compte in CompteBancaire.objects.all().order_by("nom")], required=self.required, help_text=self.help_text)
        if self.type == "modes_reglements":
            return forms.ChoiceField(label=self.label, choices=[(None, "Aucun")] + [(mode.pk, mode.label) for mode in ModeReglement.objects.all().order_by("label")], required=self.required, help_text=self.help_text)
        if self.type == "modeles_impressions_factures":
            return forms.ChoiceField(label=self.label, choices=[(None, "Aucun")] + [(modele.pk, modele.nom) for modele in ModeleImpression.objects.filter(categorie="facture").order_by("nom")], required=self.required, help_text=self.help_text)
        if self.type == "modeles_impressions_recus":
            return forms.ChoiceField(label=self.label, choices=[(None, "Aucun")] + [(modele.pk, modele.nom) for modele in ModeleImpression.objects.filter(categorie="reglement").order_by("nom")], required=self.required, help_text=self.help_text)
        if self.type == "choix":
            return forms.ChoiceField(label=self.label, choices=self.choix, required=self.required, help_text=self.help_text)
        if self.type == "decimal":
            return forms.DecimalField(label=self.label, max_digits=6, decimal_places=2, initial=0.0, required=self.required, help_text=self.help_text)
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
    # Généralités
    Parametre(code="multilingue", label="Interface multilingue", type="boolean", valeur=True, help_text="Cochez cette case pour afficher le sélecteur de langues sur le portail."),

    # Connexion
    Parametre(code="connexion_image_fond", label="Image de fond", type="image_fond", valeur=None, help_text="Sélectionnez une image de fond dans la liste. Vous pouvez ajouter de nouvelles images depuis le menu Paramétrage > Images de fond."),
    Parametre(code="connexion_adresse_exp", label="Adresse d'expédition", type="adresse_exp", valeur=None, help_text="Cette adresse mail est utilisée pour envoyer des mails de réinitialisation de mots de passe. A défaut de sélection, la fonction mot de passe oublié sera désactivée."),
    Parametre(code="connexion_question_perso", label="Activer la question personnelle de sécurité lors du changement de mot de passe", type="boolean", valeur=True, help_text="L'usager doit répondre à une question personnelle lors de la personnalisation de son mot de passe."),
    Parametre(code="connexion_afficher_nom_organisateur", label="Afficher le nom de l'organisateur", type="boolean", valeur=True, help_text="Décochez cette case si votre logo inclut déjà le nom de l'organisateur."),

    # Accueil
    Parametre(code="accueil_texte_bienvenue", label="Texte de bienvenue", type="html", valeur="Bienvenue sur le portail Famille"),
    Parametre(code="accueil_url_video", label="URL vidéo", type="char_1ligne", valeur="", help_text="Saisissez l'URL d'un tutoriel vidéo que vous souhaitez voir apparaître sur la page d'accueil. Pour insérer une vidéo Youtube, saisissez l'url 'https://www.youtube.com/embed/xxxxxx' en remplaçant les x par le code youtube de la vidéo."),
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
    Parametre(code="cotisations_afficher_page", label="Afficher la page", type="boolean", valeur=False),
    Parametre(code="cotisations_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez ici consulter les informations au sujet des adhésions."),

    # Documents
    Parametre(code="documents_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="documents_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez ici consulter ou transmettre des documents."),

    # Activités
    Parametre(code="activites_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="activites_intro", label="Texte d'introduction", type="char_2lignes", valeur="Cette page liste des activités auxquelles sont actuellement inscrits les membres de la famille."),

    # Réservations
    Parametre(code="reservations_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="reservations_intro", label="Texte d'introduction", type="char_2lignes", valeur="Sélectionnez une activité puis cliquez sur une des périodes disponibles pour accéder au calendrier des réservations correspondant."),
    Parametre(code="reservations_intro_planning", label="Texte d'introduction du planning", type="char_2lignes", valeur="Cliquez dans les cases pour ajouter ou supprimer des consommations avant de valider l'envoi des données."),
    Parametre(code="reservations_adresse_exp", label="Adresse d'expédition pour confirmation par email", type="adresse_exp", valeur=None, help_text="Cette adresse mail est utilisée pour envoyer des mails de confirmation des modifications effectuées dans les réservations."),
    Parametre(code="reservations_blocage_impayes", label="Blocage si impayés", type="choix", valeur=None, choix=[(None, "Désactivé")] + [(x, "Si impayés >= %d Euros" % x) for x in (50, 100, 200, 300, 400, 500, 1000, 1500, 2000, 3000)] + [(x+10000, "Si impayés facturés >= %d Euros" % x) for x in (50, 100, 200, 300, 400, 500, 1000, 1500, 2000, 3000)], help_text="Vous pouvez empêcher la famille d'accéder aux réservations en cas d'impayés."),

    # Facturation
    Parametre(code="facturation_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="facturation_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez consulter ici les données de facturation."),
    Parametre(code="facturation_afficher_solde_famille", label="Afficher le solde de la famille", type="boolean", valeur=False),
    Parametre(code="facturation_afficher_numero_facture", label="Afficher le numéro des factures", type="boolean", valeur=True),
    Parametre(code="facturation_afficher_solde_facture", label="Afficher le solde actuel des factures", type="boolean", valeur=True),
    Parametre(code="facturation_autoriser_detail_facture", label="Afficher le détail des factures", type="boolean", valeur=True),
    Parametre(code="facturation_autoriser_telechargement_facture", label="Autoriser le téléchargement des factures", type="boolean", valeur=True),
    Parametre(code="facturation_modele_impression_facture", label="Modèle d'impression des factures", type="modeles_impressions_factures", valeur=None, help_text="Vous devez au préalable créer un modèle d'impression pour la catégorie facture depuis le menu Paramétrage > Modèles d'impressions."),

    # Paiement en ligne
    Parametre(code="paiement_ligne_systeme", label="Paiement en ligne", type="choix", valeur=None, choix=[(None, "Aucun"), ("payfip", "PayFIP"), ("payzen", "Payzen"), ("payasso","PayAsso"), ("demo", "Mode démo")], help_text="Sélectionnez un système de paiement en ligne."),
    Parametre(code="paiement_ligne_mode_reglement", label="Mode de règlement", type="modes_reglements", valeur=None, help_text="Sélectionnez le mode de règlement qui est associé aux paiements en ligne."),
    Parametre(code="paiement_ligne_compte_bancaire", label="Compte bancaire", type="comptes_bancaires", valeur=None, help_text="Sélectionnez le compte bancaire qui est associé aux paiements en ligne."),
    Parametre(code="paiement_ligne_montant_minimal", label="Montant minimal autorisé", type="decimal", valeur=decimal.Decimal("1.00")),
    Parametre(code="paiement_ligne_multi_factures", label="Autoriser le paiement multi factures", type="boolean", valeur=False, help_text="Cochez la case pour autoriser le paiement de plusieurs factures à la fois avec un seul paiement."),
    Parametre(code="paiement_ligne_off_si_prelevement", label="Désactiver le paiement en ligne si prélèvement auto.", type="boolean", valeur=True),
    Parametre(code="payfip_mode", label="Mode de fonctionnement", type="choix", valeur="test", choix=[("test", "Test"), ("validation", "Validation"), ("production", "Production")], help_text="Sélectionnez le mode de fonctionnement."),
    Parametre(code="payzen_site_id", label="Identifiant boutique", type="char_1ligne", valeur="", help_text="Saisissez l'identifiant boutique que vous trouverez sur le backoffice Payzen."),
    Parametre(code="payzen_certificat_test", label="Certificat de test", type="char_1ligne", valeur="", help_text="Saisissez le certificat de test que vous trouverez sur le backoffice Payzen."),
    Parametre(code="payzen_certificat_production", label="Certificat de production", type="char_1ligne", valeur="", help_text="Saisissez le certificat de production que vous trouverez sur le backoffice Payzen."),
    Parametre(code="payzen_mode", label="Mode de fonctionnement", type="choix", valeur="TEST", choix=[("TEST", "Test"), ("PRODUCTION", "Production")], help_text="Sélectionnez un mode de fonctionnement."),
    Parametre(code="payzen_algo", label="Algorithme de signature", type="choix", valeur="sha1", choix=[("sha1", "SHA-1"), ("hmac_sha256", "HMAC-SHA-256")], help_text="Sélectionnez l'algorithme de signature qui a été paramétré sur votre backoffice Payzen."),
    Parametre(code="payzen_echelonnement", label="Proposer le paiement en 3 fois", type="boolean", valeur=False),

    # Règlements
    Parametre(code="reglements_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="reglements_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez consulter ici la liste de vos règlements."),
    Parametre(code="reglements_afficher_encaissement", label="Afficher la date d'encaissement", type="boolean", valeur=True),
    Parametre(code="reglements_autoriser_telechargement_recu", label="Autoriser le téléchargement du reçu", type="boolean", valeur=True),
    Parametre(code="reglements_modele_impression_recu", label="Modèle d'impression des reçus", type="modeles_impressions_recus", valeur=None, help_text="Vous devez au préalable créer un modèle d'impression pour la catégorie reçu depuis le menu Paramétrage > Modèles d'impressions."),

    # Contact
    Parametre(code="contact_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="contact_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez trouver ici les moyens de correspondre avec l'organisateur."),
    Parametre(code="messagerie_intro", label="Texte d'introduction de la messagerie", type="char_2lignes", valeur="Saisissez un message et cliquez sur le bouton Envoyer."),
    Parametre(code="messagerie_envoyer_notification_famille", label="Envoyer une notification par email des messages postés à la famille", type="boolean", valeur=True),
    Parametre(code="messagerie_envoyer_notification_admin", label="Envoyer une notification par email des messages postés à l'administrateur", type="boolean", valeur=True),
    Parametre(code="contact_afficher_coords_structures", label="Afficher les coordonnées des structures", type="boolean", valeur=True),
    Parametre(code="contact_afficher_coords_organisateur", label="Afficher les coordonnées de l'organisateur", type="boolean", valeur=True),

    # Mentions
    Parametre(code="mentions_afficher_page", label="Afficher la page", type="boolean", valeur=True),
    Parametre(code="mentions_intro", label="Texte d'introduction", type="char_2lignes", valeur="Vous pouvez consulter ici les mentions légales du portail."),
    Parametre(code="mentions_conditions_generales", label="Conditions générales d'utilisation", type="html", valeur=render_to_string("portail/modele_conditions_generales.html"), help_text="Vous pouvez insérer dans le texte les mots-clés suivants : {ORGANISATEUR_NOM},  {ORGANISATEUR_RUE}, {ORGANISATEUR_CP}, {ORGANISATEUR_VILLE}."),

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
