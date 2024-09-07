# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, InlineRadios
from core.utils.utils_commandes import Commandes
from core.models import PortailParametre
from core.utils.utils_portail import LISTE_PARAMETRES


LISTE_RUBRIQUES = [
    ("Généralités", ["multilingue"]),
    ("Page de connexion", ["connexion_image_fond", "connexion_adresse_exp", "connexion_question_perso", "connexion_afficher_nom_organisateur"]),
    ("Page d'accueil", ["accueil_texte_bienvenue", "accueil_url_video", "accueil_titre_video"]),
    ("Page des renseignements", ["renseignements_afficher_page", "renseignements_intro", "renseignements_duree_certification", "validation_auto:famille_caisse",
                                 "validation_auto:individu_identite", "validation_auto:individu_coords", "validation_auto:individu_regimes_alimentaires",
                                 "validation_auto:individu_medecin", "validation_auto:individu_maladies"]),
    ("Page des adhésions", ["cotisations_afficher_page", "cotisations_intro"]),
    ("Page des documents", ["documents_afficher_page", "documents_intro"]),
    ("Page des activités", ["activites_afficher_page", "activites_intro"]),
    ("Page des réservations", ["reservations_afficher_page", "reservations_intro", "reservations_intro_planning", "reservations_adresse_exp", "reservations_blocage_impayes",
                               "reservations_afficher_facturation", "reservations_afficher_forfaits"]),
    ("Page de la facturation", ["facturation_afficher_page", "facturation_intro", "facturation_afficher_solde_famille", "facturation_afficher_numero_facture", "facturation_afficher_solde_facture",
                                "facturation_autoriser_detail_facture", "facturation_autoriser_telechargement_facture", "facturation_modele_impression_facture"]),
    ("Paiement en ligne", ["paiement_ligne_systeme", "paiement_ligne_mode_reglement", "paiement_ligne_compte_bancaire", "paiement_ligne_montant_minimal",
                           "paiement_ligne_multi_factures", "paiement_ligne_off_si_prelevement", "payfip_mode", "payzen_site_id", "payzen_certificat_test",
                           "payzen_certificat_production", "payzen_mode", "payzen_algo", "payzen_echelonnement"]),
    ("Page des règlements", ["reglements_afficher_page", "reglements_intro", "reglements_afficher_encaissement", "reglements_autoriser_telechargement_recu", "reglements_modele_impression_recu"]),
    ("Page contact", ["contact_afficher_page", "contact_intro", "messagerie_intro", "messagerie_envoyer_notification_famille", "messagerie_envoyer_notification_admin", "contact_afficher_coords_structures", "contact_afficher_coords_organisateur"]),
    ("Page des mentions légales", ["mentions_afficher_page", "mentions_intro", "mentions_conditions_generales"]),
]


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_parametres_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Initialisation du layout
        self.helper.layout = Layout()
        self.helper.layout.append(Commandes(annuler_url="{% url 'parametrage_toc' %}", ajouter=False))

        # Importation des paramètres par défaut
        dict_parametres = {parametre.code: parametre for parametre in LISTE_PARAMETRES}
        for parametre_db in PortailParametre.objects.all():
            if parametre_db.code in dict_parametres:
                dict_parametres[parametre_db.code].From_db(parametre_db.valeur)

        # Création des fields
        for titre_rubrique, liste_parametres in LISTE_RUBRIQUES:
            liste_fields = []
            for code_parametre in liste_parametres:
                self.fields[code_parametre] = dict_parametres[code_parametre].Get_ctrl()
                self.fields[code_parametre].initial = dict_parametres[code_parametre].valeur
                liste_fields.append(Field(code_parametre))
            self.helper.layout.append(Fieldset(titre_rubrique, *liste_fields))

        self.helper.layout.append(HTML("<br>"))
        self.helper.layout.append(HTML(EXTRA_HTML))

    def clean(self):
        # Paiement en ligne
        if self.cleaned_data["paiement_ligne_systeme"]:
            if not self.cleaned_data["paiement_ligne_mode_reglement"]:
                self.add_error("paiement_ligne_mode_reglement", "Vous devez sélectionner un mode de règlement pour le paiement en ligne.")

            if self.cleaned_data["paiement_ligne_systeme"] == "payzen":
                if not self.cleaned_data["payzen_site_id"]:
                    self.add_error("payzen_site_id", "Vous devez saisir l'identifiant boutique pour le paiement en ligne.")
                if not self.cleaned_data["payzen_certificat_test"]:
                    self.add_error("payzen_certificat_test", "Vous devez saisir le certificat de test pour le paiement en ligne.")
                if not self.cleaned_data["payzen_certificat_production"]:
                    self.add_error("payzen_certificat_production", "Vous devez saisir le certificat de production pour le paiement en ligne.")

        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_paiement_ligne_systeme() {
        $('#div_id_paiement_ligne_mode_reglement').hide();
        $('#div_id_paiement_ligne_compte_bancaire').hide();
        $('#div_id_paiement_ligne_montant_minimal').hide();
        $('#div_id_paiement_ligne_multi_factures').hide();
        $('#div_id_paiement_ligne_off_si_prelevement').hide();
        $('#div_id_payfip_mode').hide();
        $('#div_id_payzen_site_id').hide();
        $('#div_id_payzen_certificat_test').hide();
        $('#div_id_payzen_certificat_production').hide();
        $('#div_id_payzen_mode').hide();
        $('#div_id_payzen_algo').hide();
        $('#div_id_payzen_echelonnement').hide();
        if ($("#id_paiement_ligne_systeme").val()) {
            $('#div_id_paiement_ligne_compte_bancaire').show();
            $('#div_id_paiement_ligne_mode_reglement').show();
            $('#div_id_paiement_ligne_montant_minimal').show();
            $('#div_id_paiement_ligne_multi_factures').show();
            $('#div_id_paiement_ligne_off_si_prelevement').show();
        };
        if ($("#id_paiement_ligne_systeme").val() == "payfip") {
            $('#div_id_payfip_mode').show();
        };
        if ($("#id_paiement_ligne_systeme").val() == "payzen") {
            $('#div_id_payzen_site_id').show();
            $('#div_id_payzen_certificat_test').show();
            $('#div_id_payzen_certificat_production').show();
            $('#div_id_payzen_mode').show();
            $('#div_id_payzen_algo').show();
            $('#div_id_payzen_echelonnement').show();
        };
    }
    $(document).ready(function() {
        $('#id_paiement_ligne_systeme').change(On_change_paiement_ligne_systeme);
        On_change_paiement_ligne_systeme.call($('#id_paiement_ligne_systeme').get(0));
    });
</script>
"""
