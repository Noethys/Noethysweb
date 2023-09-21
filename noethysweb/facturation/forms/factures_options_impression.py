# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.widgets import ColorPickerWidget
from core.utils import utils_parametres


VALEURS_DEFAUT = {
    "memoriser_parametres": False, "affichage_solde": "actuel", "afficher_impayes": True, "integrer_impayes": True, "afficher_deja_paye": True, "afficher_reste_regler": True,
    "afficher_coupon_reponse": True, "afficher_messages": True, "impayes_factures": False,
    "afficher_codes_barres": True, "afficher_reglements": True, "afficher_avis_prelevements": False, "afficher_qf_dates": True, "afficher_titre": True, "texte_titre": "Facture",
    "taille_texte_titre": 19, "afficher_periode": True, "taille_texte_periode": 8, "affichage_prestations": "0", "intitules": "0", "couleur_fond_1": "#D9D9D9",
    "couleur_fond_2": "#F1F1F1", "largeur_colonne_date": 50, "largeur_colonne_montant_ht": 50, "largeur_colonne_montant_tva": 50, "largeur_colonne_montant_ttc": 70,
    "taille_texte_individu": 7, "taille_texte_activite": 7, "taille_texte_noms_colonnes": 5, "taille_texte_prestation": 7, "taille_texte_messages": 7,
    "taille_texte_labels_totaux": 9, "taille_texte_montants_totaux": 10, "texte_prestations_anterieures": "Des prestations antérieures ont été reportées sur cette facture.",
    "taille_texte_prestations_anterieures": 5,
    "texte_introduction": "", "taille_texte_introduction": 9, "style_texte_introduction": "0", "couleur_fond_introduction": "#FFFFFF",
    "couleur_bord_introduction": "#FFFFFF", "alignement_texte_introduction": "0", "texte_conclusion": "", "taille_texte_conclusion": 9,
    "style_texte_conclusion": "0", "couleur_fond_conclusion": "#FFFFFF", "couleur_bord_conclusion": "#FFFFFF", "alignement_texte_conclusion": "0",
}


class Formulaire(FormulaireBase, forms.Form):
    memoriser_parametres = forms.BooleanField(label="Mémoriser les paramètres", initial=VALEURS_DEFAUT["memoriser_parametres"], required=False)

    affichage_solde = forms.ChoiceField(label="Afficher le solde", choices=[("0", "Actuel"), ("1", "Initial")], initial=VALEURS_DEFAUT["affichage_solde"], required=False)
    afficher_impayes = forms.BooleanField(label="Afficher le rappel des impayés", initial=VALEURS_DEFAUT["afficher_impayes"], required=False)
    integrer_impayes = forms.BooleanField(label="Intégrer les impayés au solde", initial=VALEURS_DEFAUT["integrer_impayes"], required=False)
    impayes_factures = forms.BooleanField(label="Intégrer uniquement les impayés facturés", initial=VALEURS_DEFAUT["impayes_factures"], required=False)
    afficher_deja_paye = forms.BooleanField(label="Afficher la case du montant déjà réglé", initial=VALEURS_DEFAUT["afficher_deja_paye"], required=False)
    afficher_reste_regler = forms.BooleanField(label="Afficher la case du solde à régler", initial=VALEURS_DEFAUT["afficher_reste_regler"], required=False)
    afficher_coupon_reponse = forms.BooleanField(label="Afficher le coupon-réponse", initial=VALEURS_DEFAUT["afficher_coupon_reponse"], required=False)
    afficher_messages = forms.BooleanField(label="Afficher les messages", initial=VALEURS_DEFAUT["afficher_messages"], required=False)
    afficher_codes_barres = forms.BooleanField(label="Afficher les codes-barres", initial=VALEURS_DEFAUT["afficher_codes_barres"], required=False)
    afficher_reglements = forms.BooleanField(label="Afficher les règlements", initial=VALEURS_DEFAUT["afficher_reglements"], required=False)
    afficher_avis_prelevements = forms.BooleanField(label="Afficher les avis de prélèvements", initial=VALEURS_DEFAUT["afficher_avis_prelevements"], required=False)
    afficher_qf_dates = forms.BooleanField(label="Afficher les quotients familiaux", initial=VALEURS_DEFAUT["afficher_qf_dates"], required=False)

    afficher_titre = forms.BooleanField(label="Afficher le titre", initial=VALEURS_DEFAUT["afficher_titre"], required=False)
    texte_titre = forms.CharField(label="Titre du document", initial=VALEURS_DEFAUT["texte_titre"], required=True)
    taille_texte_titre = forms.IntegerField(label="Taille de texte du titre", initial=VALEURS_DEFAUT["taille_texte_titre"], required=True)
    afficher_periode = forms.BooleanField(label="Afficher la période de facturation", initial=VALEURS_DEFAUT["afficher_periode"], required=False)
    taille_texte_periode = forms.IntegerField(label="Taille de texte de la période", initial=VALEURS_DEFAUT["taille_texte_periode"], required=True)

    affichage_prestations = forms.ChoiceField(label="Affichage des prestations", choices=[("0", "Détaillé"), ("1", "Regroupement par label"), ("2", "Regroupement par label et par montant unitaire"), ("3", "Regroupement par label + dates"), ("4", "Regroupement par label et montant unitaire + dates")], initial=VALEURS_DEFAUT["affichage_prestations"], required=True)
    intitules = forms.ChoiceField(label="Intitulé des prestations", choices=[("0", "Intitulé original"), ("1", "Intitulé original + état absence injustifiée"), ("2", "Nom du tarif"), ("3", "Nom de l'activité")], initial=VALEURS_DEFAUT["intitules"], required=True)
    couleur_fond_1 = forms.CharField(label="Couleur de fond 1", required=True, widget=ColorPickerWidget(), initial=VALEURS_DEFAUT["couleur_fond_1"])
    couleur_fond_2 = forms.CharField(label="Couleur de fond 2", required=True, widget=ColorPickerWidget(), initial=VALEURS_DEFAUT["couleur_fond_2"])
    largeur_colonne_date = forms.IntegerField(label="Largeur de la colonne Date", initial=VALEURS_DEFAUT["largeur_colonne_date"], required=True)
    largeur_colonne_montant_ht = forms.IntegerField(label="Largeur de la colonne Montant HT", initial=VALEURS_DEFAUT["largeur_colonne_montant_ht"], required=True)
    largeur_colonne_montant_tva = forms.IntegerField(label="Largeur de la colonne Montant TVA", initial=VALEURS_DEFAUT["largeur_colonne_montant_tva"], required=True)
    largeur_colonne_montant_ttc = forms.IntegerField(label="Largeur de la colonne Montant TTC", initial=VALEURS_DEFAUT["largeur_colonne_montant_ttc"], required=True)
    taille_texte_individu = forms.IntegerField(label="Taille de texte de l'individu", initial=VALEURS_DEFAUT["taille_texte_individu"], required=True)
    taille_texte_activite = forms.IntegerField(label="Taille de texte de l'activité", initial=VALEURS_DEFAUT["taille_texte_activite"], required=True)
    taille_texte_noms_colonnes = forms.IntegerField(label="Taille de texte des noms de colonnes", initial=VALEURS_DEFAUT["taille_texte_noms_colonnes"], required=True)
    taille_texte_prestation = forms.IntegerField(label="Taille de texte des prestations", initial=VALEURS_DEFAUT["taille_texte_prestation"], required=True)
    taille_texte_messages = forms.IntegerField(label="Taille de texte des messages", initial=VALEURS_DEFAUT["taille_texte_messages"], required=True)
    taille_texte_labels_totaux = forms.IntegerField(label="Taille de texte des labels totaux", initial=VALEURS_DEFAUT["taille_texte_labels_totaux"], required=True)
    taille_texte_montants_totaux = forms.IntegerField(label="Taille de texte des montants totaux", initial=VALEURS_DEFAUT["taille_texte_montants_totaux"], required=True)

    taille_texte_prestations_anterieures = forms.IntegerField(label="Taille de texte du commentaire", initial=VALEURS_DEFAUT["taille_texte_prestations_anterieures"], required=True)
    texte_prestations_anterieures = forms.CharField(label="Texte d'information", initial=VALEURS_DEFAUT["texte_prestations_anterieures"], required=True)

    texte_introduction = forms.CharField(label="Texte d'introduction", initial=VALEURS_DEFAUT["texte_introduction"], required=False)
    taille_texte_introduction = forms.IntegerField(label="Taille de texte d'introduction", initial=VALEURS_DEFAUT["taille_texte_introduction"], required=True)
    style_texte_introduction = forms.ChoiceField(label="Style du texte d'introduction", choices=[("0", "Normal"), ("1", "Italique"), ("2", "Gras"), ("3", "Italique + gras")], initial=VALEURS_DEFAUT["style_texte_introduction"], required=True)
    couleur_fond_introduction = forms.CharField(label="Couleur de fond introduction", required=True, widget=ColorPickerWidget(), initial=VALEURS_DEFAUT["couleur_fond_introduction"])
    couleur_bord_introduction = forms.CharField(label="Couleur de bord introduction", required=True, widget=ColorPickerWidget(), initial=VALEURS_DEFAUT["couleur_bord_introduction"])
    alignement_texte_introduction = forms.ChoiceField(label="Alignement du texte d'introduction", choices=[("0", "Gauche"), ("1", "Centre"), ("2", "Droite")], initial=VALEURS_DEFAUT["alignement_texte_introduction"], required=True)

    texte_conclusion = forms.CharField(label="Texte de conclusion", initial=VALEURS_DEFAUT["texte_conclusion"], required=False)
    taille_texte_conclusion = forms.IntegerField(label="Taille de texte de conclusion", initial=VALEURS_DEFAUT["taille_texte_conclusion"], required=True)
    style_texte_conclusion = forms.ChoiceField(label="Style du texte de conclusion", choices=[("0", "Normal"), ("1", "Italique"), ("2", "Gras"), ("3", "Italique + gras")], initial=VALEURS_DEFAUT["style_texte_conclusion"], required=True)
    couleur_fond_conclusion = forms.CharField(label="Couleur de fond conclusion", required=True, widget=ColorPickerWidget(), initial=VALEURS_DEFAUT["couleur_fond_conclusion"])
    couleur_bord_conclusion = forms.CharField(label="Couleur de bord conclusion", required=True, widget=ColorPickerWidget(), initial=VALEURS_DEFAUT["couleur_bord_conclusion"])
    alignement_texte_conclusion = forms.ChoiceField(label="Alignement du texte de conclusion", choices=[("0", "Gauche"), ("1", "Centre"), ("2", "Droite")], initial=VALEURS_DEFAUT["alignement_texte_conclusion"], required=True)

    def __init__(self, *args, **kwargs):
        self.memorisation = kwargs.pop("memorisation", True)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'options_impression_form'
        self.helper.form_method = 'post'

        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-md-4'
        # self.helper.field_class = 'col-md-8'

        # Importation des paramètres
        if self.memorisation:
            parametres = {nom: field.initial for nom, field in self.fields.items()}
            del parametres["memoriser_parametres"]
            parametres = utils_parametres.Get_categorie(categorie="impression_facture", utilisateur=self.request.user, parametres=parametres)
            for nom, valeur in parametres.items():
                self.fields[nom].initial = valeur

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Eléments à afficher",
                Field("affichage_solde"),
                Field("afficher_impayes"),
                Field("integrer_impayes"),
                Field("impayes_factures"),
                Field("afficher_deja_paye"),
                Field("afficher_reste_regler"),
                Field("afficher_coupon_reponse"),
                Field("afficher_messages"),
                Field("afficher_codes_barres"),
                Field("afficher_reglements"),
                Field("afficher_avis_prelevements"),
                Field("afficher_qf_dates"),
            ),
            Fieldset("Titre",
                Field("afficher_titre"),
                Field("texte_titre"),
                Field("taille_texte_titre"),
                Field("afficher_periode"),
                Field("taille_texte_periode"),
            ),
            Fieldset("Tableau des prestations",
                Field("affichage_prestations"),
                Field("intitules"),
                Field("couleur_fond_1"),
                Field("couleur_fond_2"),
                Field("largeur_colonne_date"),
                Field("largeur_colonne_montant_ht"),
                Field("largeur_colonne_montant_tva"),
                Field("largeur_colonne_montant_ttc"),
                Field("taille_texte_individu"),
                Field("taille_texte_activite"),
                Field("taille_texte_noms_colonnes"),
                Field("taille_texte_prestation"),
                Field("taille_texte_messages"),
                Field("taille_texte_labels_totaux"),
                Field("taille_texte_montants_totaux"),
            ),
            Fieldset("Prestations antérieures",
                Field("taille_texte_prestations_anterieures"),
                Field("texte_prestations_anterieures"),
            ),
            Fieldset("Texte d'introduction",
                Field("texte_introduction"),
                Field("taille_texte_introduction"),
                Field("style_texte_introduction"),
                Field("couleur_fond_introduction"),
                Field("couleur_bord_introduction"),
                Field("alignement_texte_introduction"),
            ),
            Fieldset("Texte de conclusion",
                Field("texte_conclusion"),
                Field("taille_texte_conclusion"),
                Field("style_texte_conclusion"),
                Field("couleur_fond_conclusion"),
                Field("couleur_bord_conclusion"),
                Field("alignement_texte_conclusion"),
            ),
        )

        if self.memorisation:
            self.helper.layout.insert(0,
                Fieldset("Mémorisation",
                    Field("memoriser_parametres"),
                ),
            )

    def clean(self):
        if self.memorisation and self.cleaned_data["memoriser_parametres"]:
            parametres = copy.copy(self.cleaned_data)
            del parametres["memoriser_parametres"]
            utils_parametres.Set_categorie(categorie="impression_facture", utilisateur=self.request.user, parametres=parametres)
