# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget
from core.forms.select2 import Select2MultipleWidget
from core.utils import utils_questionnaires
from core.forms.base import FormulaireBase


def Get_regroupements():
    liste_regroupements = [
        ("", "Aucun"), ("jour", "Jour"), ("mois", "Mois"), ("annee", "Année"),
        ("label_prestation", "Label de la prestation"), ("activite", "Activité"), ("code_comptable", "Code comptable"), ("code_analytique", "Code analytique"),
        ("categorie_tarif", "Catégorie de tarif"), ("famille", "Famille"), ("individu", "Individu"),
        ("ville_residence", "Ville de résidence"), ("secteur", "Secteur géographique"), ("age", "Age"),
        ("ville_naissance", "Ville de naissance"), ("nom_ecole", "Ecole"), ("nom_classe", "Classe"),
        ("nom_niveau_scolaire", "Niveau scolaire"), ("regime", "Régime social"), ("caisse", "Caisse d'allocations"),
        ("qf_tarifs", "Quotient familial - Tranches tarifs"), ("qf_100", "Quotient familial - Tranches de 100"), ]

    # Intégration des questionnaires
    q = utils_questionnaires.Questionnaires()
    for public in ("famille", "individu"):
        for dictTemp in q.GetQuestions(public):
            label = "Question %s. : %s" % (public[:3], dictTemp["label"])
            code = "question_%s_%d" % (public, dictTemp["IDquestion"])
            liste_regroupements.append((code, label))

    return liste_regroupements


def Get_modes():
    liste_modes = [
        ("nbre", "Nombre de prestations"), ("facture", "Montant des prestations"),
        ("facture_ht", "Montant des prestations HT"), ("facture_tva", "Montant de la TVA"),
        ("regle", "Montant des prestations réglées"), ("impaye", "Montant des prestations impayées"),
        ("nbre_facturees", "Nombre de prestations facturées"),
        ("facture_facturees", "Montant des prestations facturées"),
        ("regle_facturees", "Montant des prestations réglées et facturées"),
        ("impaye_facturees", "Montant des prestations impayées et facturées"),
        ("nbre_nonfacturees", "Nombre de prestations non facturées"),
        ("facture_nonfacturees", "Montant des prestations non facturées"),
        ("regle_nonfacturees", "Montant des prestations réglées et non facturées"),
        ("impaye_nonfacturees", "Montant des prestations impayées et non facturées"), ]
    return liste_modes


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    donnees = forms.MultipleChoiceField(label="Type de prestation", required=True, widget=Select2MultipleWidget(), choices=[("cotisation", "Cotisations"), ("consommation", "Consommations"), ("location", "Locations"), ("autre", "Autres")], initial=["cotisation", "consommation", "location", "autre"])
    filtre_reglements_saisis = forms.CharField(label="Règlements saisis sur une période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    filtre_reglements_deposes = forms.CharField(label="Règlements déposés sur une période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    donnee_ligne = forms.ChoiceField(label="Ligne", choices=Get_regroupements(), initial="activite", required=False)
    donnee_colonne = forms.ChoiceField(label="Colonne", choices=Get_regroupements(), initial="mois", required=False)
    donnee_detail = forms.ChoiceField(label="Ligne de détail", choices=Get_regroupements(), initial="label_prestation", required=False)
    donnee_case = forms.ChoiceField(label="Case", choices=Get_modes(), initial="facture", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Fieldset("Données",
                Field('periode'),
                Field('activites'),
            ),
            Fieldset("Affichage",
                Field('donnee_ligne'),
                Field('donnee_colonne'),
                Field('donnee_detail'),
                Field('donnee_case'),
            ),
            Fieldset("Filtres",
                Field('donnees'),
                Field('filtre_reglements_saisis'),
                Field('filtre_reglements_deposes'),
            ),
        )


