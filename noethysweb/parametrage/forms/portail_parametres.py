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
    ("Page de connexion", ["connexion_image_fond", "connexion_adresse_exp", ]),
    ("Page d'accueil", ["accueil_texte_bienvenue", "accueil_url_video", "accueil_titre_video"]),
    ("Page des renseignements", ["renseignements_afficher_page", "renseignements_intro", "validation_auto:famille_caisse", "validation_auto:individu_identite",
                                 "validation_auto:individu_coords", "validation_auto:individu_regimes_alimentaires", "validation_auto:individu_maladies",
                                 "validation_auto:individu_medecin"]),
    ("Page des documents", ["documents_afficher_page", "documents_intro"]),
    ("Page des réservations", ["reservations_afficher_page", "reservations_intro", "reservations_intro_planning"]),
    ("Page de la facturation", ["facturation_afficher_page", "facturation_intro", "facturation_afficher_numero_facture", "facturation_afficher_solde_facture", "facturation_autoriser_detail_facture", "facturation_autoriser_telechargement_facture"]),
    ("Page des règlements", ["reglements_afficher_page", "reglements_intro", "reglements_afficher_encaissement", "reglements_autoriser_telechargement_recu"]),
    ("Page contact", ["contact_afficher_page", "contact_intro", "messagerie_intro", "messagerie_envoyer_notification", "contact_afficher_coords_structures", "contact_afficher_coords_organisateur"]),
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
