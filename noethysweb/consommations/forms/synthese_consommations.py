# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, Select_activite
from core.utils import utils_questionnaires
from core.models import Activite
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activite = forms.ModelChoiceField(label="Activité", queryset=Activite.objects.all(), required=True, widget=Select_activite())
    afficher_detail_groupe = forms.BooleanField(label="Afficher détail par groupe", initial=False, required=False)

    donnees = forms.ChoiceField(label="Données", choices=[("quantite", "Quantité"), ("temps_presence", "Temps de présence"), ("temps_facture", "Temps facturé")], initial="quantite", required=False)

    choix_regroupement = [
        ("jour", "Jour"), ("mois", "Mois"), ("annee", "Année"), ("activite", "Activité"), ("groupe", "Groupe"),
        ("evenement", "Evènement"), ("evenement_date", "Evènement (avec date)"), ("categorie_tarif", "Catégorie de tarif"),
        ("ville_residence", "Ville de résidence"), ("secteur", "Secteur géographique"), ("genre", "Genre (M/F)"),
        ("age", "Age"), ("ville_naissance", "Ville de naissance"), ("nom_ecole", "Ecole"), ("nom_classe", "Classe"),
        ("nom_niveau_scolaire", "Niveau scolaire"), ("famille", "Famille"), ("individu", "Individu"), ("regime", "Régime social"),
        ("caisse", "Caisse d'allocations"), ("qf", "Quotient familial"), ("categorie_travail", "Catégorie de travail"),
        ("categorie_travail_pere", "Catégorie de travail du père"), ("categorie_travail_mere", "Catégorie de travail de la mère"),
    ]
    q = utils_questionnaires.Questionnaires()
    for public in ("famille", "individu"):
        for dictTemp in q.GetQuestions(public):
            label = "Question %s. : %s" % (public[:3], dictTemp["label"])
            code = "question_%s_%d" % (public, dictTemp["IDquestion"])
            choix_regroupement.append((code, label))
    regroupement = forms.ChoiceField(label="Regroupement", widget=Select2Widget(), choices=choix_regroupement, required=True)

    etats = forms.MultipleChoiceField(required=True, widget=Select2MultipleWidget(), choices=[("reservation", "Réservation"), ("present", "Présent"), ("attente", "Attente"), ("refus", "Refus"), ("absentj", "Absence justifiée"), ("absenti", "Absence injustifiée")], initial=["reservation", "present"])

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request

        self.helper.layout = Layout(
            Field('periode'),
            Field('activite'),
            Field('afficher_detail_groupe'),
            Field('donnees'),
            Field('regroupement'),
            Field('etats'),
        )

    def clean(self):
        return self.cleaned_data