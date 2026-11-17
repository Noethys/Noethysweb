# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Formulaires des éditions du module Collaborateurs : sélection commune des collaborateurs et options propres à chaque édition """

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.forms.select2 import Select2MultipleWidget
from core.models import GroupeCollaborateurs, TypeCongeCollaborateur, TypeQualificationCollaborateur
from core.widgets import DatePickerWidget, DateRangePickerWidget
from collaborateurs.forms.planning_absences import Get_choix_mois
from collaborateurs.forms.variables_paie import Get_mois_defaut

CHOIX_SITUATION = [("en_poste", "En poste aujourd'hui"), ("a_venir", "En poste ou dont le contrat est à venir"), ("tous", "Tous les collaborateurs")]
CHOIX_ORIENTATION = [("PORTRAIT", "Portrait"), ("PAYSAGE", "Paysage")]


class Formulaire_base(FormulaireBase, forms.Form):
    """ Sélection des collaborateurs proposés dans la liste """
    situation_defaut = "en_poste"
    champs_options = []         # Champs propres à l'édition, affichés dans le cadre Options
    champs_defilement = []      # Listes de cases à cocher affichées dans une zone à barre de défilement

    situation = forms.ChoiceField(label="Collaborateurs", choices=CHOIX_SITUATION, required=True)
    groupes = forms.ModelMultipleChoiceField(label="Groupes de collaborateurs", queryset=GroupeCollaborateurs.objects.all().order_by("nom"), required=False,
                                             widget=Select2MultipleWidget({"data-minimum-input-length": 0}), help_text="Laissez vide pour tous les groupes.")

    def __init__(self, *args, **kwargs):
        super(Formulaire_base, self).__init__(*args, **kwargs)
        self.fields["situation"].initial = self.situation_defaut
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = "post"
        self.helper.form_tag = True
        selection = [Field(nom) for nom in self.Champs_selection()]
        options = [Field(nom, wrapper_class="ed_defilement") if nom in self.champs_defilement else Field(nom) for nom in self.champs_options]
        self.helper.layout = Layout(Fieldset("Sélection", *selection), *([Fieldset("Options", *options)] if options else []))

    def Champs_selection(self):
        return ["situation", "groupes"]

    def Get_parametres(self):
        """ Valeurs du formulaire sans validation (affichage initial de la page) """
        return {nom: champ.initial for nom, champ in self.fields.items()}


# ------------------------------------------------- Dossiers et listes -------------------------------------------------

class Formulaire_fiches(Formulaire_base):
    rubriques = forms.MultipleChoiceField(label="Rubriques", widget=forms.CheckboxSelectMultiple, required=True,
                                          choices=[("identite", "Identité et coordonnées"), ("groupes", "Groupes et qualifications"), ("contrats", "Contrats"),
                                                   ("pieces", "Pièces"), ("questionnaire", "Questionnaire"), ("memo", "Mémo")],
                                          initial=["identite", "groupes", "contrats", "pieces", "questionnaire", "memo"])
    afficher_photo = forms.BooleanField(label="Afficher la photo", required=False, initial=True)
    masquer_vides = forms.BooleanField(label="Masquer les informations non renseignées", required=False, initial=True)
    champs_options = ["rubriques", "afficher_photo", "masquer_vides"]


class Formulaire_trombinoscope(Formulaire_base):
    titre = forms.CharField(label="Titre", required=True, initial="Trombinoscope de l'équipe", max_length=200)
    regroupement = forms.ChoiceField(label="Regroupement", choices=[("AUCUN", "Aucun"), ("GROUPE", "Par groupe de collaborateurs"), ("POSTE", "Par poste")], initial="GROUPE")
    nbre_colonnes = forms.TypedChoiceField(label="Photos par ligne", choices=[(n, str(n)) for n in (2, 3, 4, 5, 6)], coerce=int, initial=5)
    afficher_poste = forms.BooleanField(label="Afficher le poste", required=False, initial=True)
    afficher_telephone = forms.BooleanField(label="Afficher le téléphone portable", required=False, initial=False)
    saut_page = forms.BooleanField(label="Un groupe par page", required=False, initial=False)
    champs_options = ["titre", "regroupement", "nbre_colonnes", "afficher_poste", "afficher_telephone", "saut_page"]


class Formulaire_telephones(Formulaire_base):
    titre = forms.CharField(label="Titre", required=True, initial="Liste téléphonique de l'équipe", max_length=200)
    colonnes = forms.MultipleChoiceField(label="Colonnes", widget=forms.CheckboxSelectMultiple, required=True,
                                         choices=[("poste", "Poste"), ("tel_mobile", "Tél. portable"), ("tel_domicile", "Tél. domicile"), ("travail_tel", "Tél. professionnel"),
                                                  ("mail", "Email personnel"), ("travail_mail", "Email professionnel")],
                                         initial=["poste", "tel_mobile", "travail_tel", "travail_mail"])
    regroupement = forms.ChoiceField(label="Regroupement", choices=[("AUCUN", "Aucun"), ("GROUPE", "Par groupe de collaborateurs")], initial="AUCUN")
    orientation = forms.ChoiceField(label="Orientation", choices=CHOIX_ORIENTATION, initial="PORTRAIT")
    champs_options = ["titre", "colonnes", "regroupement", "orientation"]


COLONNES_LISTE = [
    ("civilite", "Civilité"), ("nom", "Nom"), ("prenom", "Prénom"), ("nom_jfille", "Nom de naissance"), ("date_naiss", "Date de naissance"), ("age", "Âge"),
    ("nationalite", "Nationalité"), ("adresse", "Adresse"), ("cp_resid", "Code postal"), ("ville_resid", "Ville"), ("tel_mobile", "Tél. portable"),
    ("tel_domicile", "Tél. domicile"), ("travail_tel", "Tél. professionnel"), ("mail", "Email personnel"), ("travail_mail", "Email professionnel"),
    ("groupes", "Groupes"), ("qualifications", "Qualifications"), ("poste", "Poste"), ("type_contrat", "Type de contrat"), ("contrat_debut", "Début du contrat"),
    ("contrat_fin", "Fin du contrat"), ("heures_hebdo", "Heures hebdo."), ("anciennete", "Ancienneté"), ("idcollaborateur", "ID"),
]


class Formulaire_liste(Formulaire_base):
    titre = forms.CharField(label="Titre", required=True, initial="Listing des collaborateurs", max_length=200)
    colonnes = forms.MultipleChoiceField(label="Colonnes", widget=forms.CheckboxSelectMultiple, required=True, choices=COLONNES_LISTE,
                                         initial=["nom", "prenom", "poste", "type_contrat", "contrat_debut", "contrat_fin", "tel_mobile", "travail_mail"])
    tri = forms.ChoiceField(label="Tri", choices=[("nom", "Nom"), ("poste", "Poste"), ("contrat_debut", "Début du contrat"), ("ville_resid", "Ville")], initial="nom")
    orientation = forms.ChoiceField(label="Orientation", choices=CHOIX_ORIENTATION, initial="PAYSAGE")
    champs_options = ["titre", "colonnes", "tri", "orientation"]
    champs_defilement = ["colonnes"]


GABARITS_ETIQUETTES = {
    "L7160": {"label": "Étiquettes 63,5 x 38,1 mm (21 par page, type Avery L7160)", "largeur": 63.5, "hauteur": 38.1, "colonnes": 3, "lignes": 7, "marge_haut": 15.1, "marge_gauche": 7.2, "espace_h": 2.5, "espace_v": 0},
    "L7163": {"label": "Étiquettes 99,1 x 38,1 mm (14 par page, type Avery L7163)", "largeur": 99.1, "hauteur": 38.1, "colonnes": 2, "lignes": 7, "marge_haut": 15.1, "marge_gauche": 4.7, "espace_h": 2.5, "espace_v": 0},
    "L7165": {"label": "Étiquettes 99,1 x 67,7 mm (8 par page, type Avery L7165)", "largeur": 99.1, "hauteur": 67.7, "colonnes": 2, "lignes": 4, "marge_haut": 13.1, "marge_gauche": 4.7, "espace_h": 2.5, "espace_v": 0},
    "BADGE": {"label": "Badges 86 x 54 mm, format carte (10 par page)", "largeur": 86, "hauteur": 54, "colonnes": 2, "lignes": 5, "marge_haut": 13.5, "marge_gauche": 15, "espace_h": 8, "espace_v": 0},
    "BADGE_GRAND": {"label": "Badges 90 x 120 mm, porte-badge (4 par page)", "largeur": 90, "hauteur": 120, "colonnes": 2, "lignes": 2, "marge_haut": 20, "marge_gauche": 12, "espace_h": 6, "espace_v": 8},
}


class Formulaire_etiquettes(Formulaire_base):
    modele = forms.ChoiceField(label="Modèle", choices=[("ADRESSE", "Étiquette d'adresse"), ("NOM", "Étiquette nominative (nom et poste)"), ("BADGE", "Badge avec photo")], initial="BADGE")
    gabarit = forms.ChoiceField(label="Format", choices=[(code, valeurs["label"]) for code, valeurs in GABARITS_ETIQUETTES.items()], initial="BADGE")
    texte_badge = forms.CharField(label="Texte du badge", required=False, max_length=100, help_text="Affiché en haut du badge. Laissez vide pour le nom de l'organisateur.")
    afficher_poste = forms.BooleanField(label="Afficher le poste", required=False, initial=True)
    nbre_copies = forms.IntegerField(label="Nombre d'exemplaires", min_value=1, max_value=50, initial=1)
    premiere_position = forms.IntegerField(label="Commencer à l'emplacement n°", min_value=1, max_value=50, initial=1, help_text="Pour réutiliser une planche déjà entamée.")
    contours = forms.BooleanField(label="Afficher les contours", required=False, initial=True)
    champs_options = ["modele", "gabarit", "texte_badge", "afficher_poste", "nbre_copies", "premiere_position", "contours"]


# ------------------------------------------------- Réglementaire -------------------------------------------------

class Formulaire_registre(Formulaire_base):
    situation_defaut = "tous"
    periode = forms.CharField(label="Contrats en cours sur la période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}),
                              help_text="Laissez décoché pour imprimer le registre complet depuis la première embauche.")
    afficher_heures = forms.BooleanField(label="Préciser le temps partiel (heures hebdomadaires)", required=False, initial=True)
    champs_options = ["periode", "afficher_heures"]


class Formulaire_qualifications(Formulaire_base):
    date = forms.DateField(label="Date de référence", required=True, widget=DatePickerWidget(), help_text="Date à laquelle la validité des pièces est contrôlée.")
    qualifications = forms.ModelMultipleChoiceField(label="Qualifications", queryset=TypeQualificationCollaborateur.objects.all().order_by("nom"),
                                                    widget=forms.CheckboxSelectMultiple, required=True)
    afficher_dates = forms.BooleanField(label="Afficher la date de fin de validité des pièces", required=False, initial=True)
    champs_options = ["date", "qualifications", "afficher_dates"]
    champs_defilement = ["qualifications"]

    def __init__(self, *args, **kwargs):
        super(Formulaire_qualifications, self).__init__(*args, **kwargs)
        self.fields["date"].initial = datetime.date.today()
        # Par défaut : les qualifications détenues par au moins un collaborateur
        self.fields["qualifications"].initial = list(TypeQualificationCollaborateur.objects.filter(collaborateur_qualifications__isnull=False).distinct().values_list("pk", flat=True))


# ------------------------------------------------- Congés et temps de travail -------------------------------------------------

class Formulaire_attestations_conges(Formulaire_base):
    date = forms.DateField(label="Situation au", required=True, widget=DatePickerWidget(), help_text="Les compteurs affichés sont ceux de la période de référence qui contient cette date.")
    types = forms.ModelMultipleChoiceField(label="Types de congés", queryset=TypeCongeCollaborateur.objects.all().order_by("ordre", "nom"), widget=forms.CheckboxSelectMultiple, required=True)
    afficher_detail = forms.BooleanField(label="Détailler les absences de la période", required=False, initial=True)
    afficher_signature = forms.BooleanField(label="Ajouter une zone de signature", required=False, initial=True)
    champs_options = ["date", "types", "afficher_detail", "afficher_signature"]

    def __init__(self, *args, **kwargs):
        super(Formulaire_attestations_conges, self).__init__(*args, **kwargs)
        self.fields["date"].initial = datetime.date.today()
        self.fields["types"].initial = list(TypeCongeCollaborateur.objects.values_list("pk", flat=True))


class Formulaire_demandes_absences(Formulaire_base):
    situation_defaut = "tous"
    periode = forms.CharField(label="Absences sur la période", required=True, widget=DateRangePickerWidget())
    etats = forms.MultipleChoiceField(label="Etats", widget=forms.CheckboxSelectMultiple, required=True,
                                      choices=[("ATTENTE", "En attente"), ("VALIDEE", "Validées"), ("REFUSEE", "Refusées"), ("ANNULEE", "Annulées")], initial=["ATTENTE", "VALIDEE"])
    afficher_solde = forms.BooleanField(label="Afficher le solde du compteur", required=False, initial=True)
    deux_par_page = forms.BooleanField(label="Deux demandes par page", required=False, initial=True)
    champs_options = ["periode", "etats", "afficher_solde", "deux_par_page"]

    def __init__(self, *args, **kwargs):
        super(Formulaire_demandes_absences, self).__init__(*args, **kwargs)
        aujourdhui = datetime.date.today()
        self.fields["periode"].initial = "%s;%s" % (aujourdhui - datetime.timedelta(days=30), aujourdhui + datetime.timedelta(days=90))


class Formulaire_releves_heures(Formulaire_base):
    mois = forms.ChoiceField(label="Mois", choices=[], required=True)
    donnees = forms.ChoiceField(label="Heures retenues", choices=[("REALISE", "Réalisé si saisi, sinon planifié"), ("PLANIFIE", "Planifié")], initial="REALISE")
    afficher_affectations = forms.BooleanField(label="Afficher les affectations", required=False, initial=True)
    afficher_jours_vides = forms.BooleanField(label="Afficher les jours sans évènement", required=False, initial=False)
    afficher_signature = forms.BooleanField(label="Ajouter une zone de signature", required=False, initial=True)
    champs_options = ["mois", "donnees", "afficher_affectations", "afficher_jours_vides", "afficher_signature"]

    def __init__(self, *args, **kwargs):
        super(Formulaire_releves_heures, self).__init__(*args, **kwargs)
        self.fields["mois"].choices = Get_choix_mois(nbre_avant=24, nbre_apres=2)
        self.fields["mois"].initial = Get_mois_defaut()
