# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    regroupement_lignes = forms.ChoiceField(label="Lignes", choices=[("activites", "Activité"), ("familles", "Famille")], initial="activites", required=False)
    regroupement_colonnes = forms.ChoiceField(label="Colonnes", choices=[("mois", "Mois"), ("annee", "Année")], initial="mois", required=False)
    afficher_detail = forms.BooleanField(label="Afficher la ligne de détail", initial=True, required=False)
    donnees = forms.MultipleChoiceField(label="Type de prestation", required=True, widget=Select2MultipleWidget(), choices=[("cotisation", "Cotisations"), ("consommation", "Consommations"), ("location", "Locations"), ("autre", "Autres")], initial=["cotisation", "consommation", "location", "autre"])
    filtre_reglements_saisis = forms.CharField(label="Règlements saisis sur une période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    filtre_reglements_deposes = forms.CharField(label="Règlements déposés sur une période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))

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
                Field('regroupement_lignes'),
                Field('afficher_detail'),
                Field('regroupement_colonnes'),
            ),
            Fieldset("Filtres",
                Field('donnees'),
                Field('filtre_reglements_saisis'),
                Field('filtre_reglements_deposes'),
            ),
        )
