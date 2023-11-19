# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget
from core.forms.select2 import Select2MultipleWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    type_reglements = forms.ChoiceField(label="Type de règlements", choices=[("saisis", "Saisis"), ("deposes", "Déposés"), ("non_deposes", "Non déposés")], initial="saisis", required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    types_prestations = forms.MultipleChoiceField(label="Type de prestation", required=True, widget=Select2MultipleWidget(), choices=[("cotisation", "Cotisations"), ("consommation", "Consommations"), ("location", "Locations"), ("autre", "Autres"), ("avoir", "Avoirs")], initial=["cotisation", "consommation", "location", "autre", "avoir"])
    ventilation = forms.CharField(label="Les prestations ventilés sur une période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Fieldset("Données",
                Field('type_reglements'),
                Field('periode'),
            ),
            Fieldset("Filtres",
                Field('activites'),
                Field('types_prestations'),
                Field('ventilation'),
            ),
        )


