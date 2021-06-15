# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget, DatePickerWidget
import datetime


class Formulaire(FormulaireBase, forms.Form):
    date = forms.DateField(label="Date de référence", required=True, widget=DatePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    presents = forms.CharField(label="Uniquement les présents", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    masquer_complets = forms.BooleanField(label="Masquer les dossiers complets", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.fields['date'].initial = datetime.date.today()

        self.helper.layout = Layout(
            Field('date'),
            Field('activites'),
            Field('presents'),
            Field('masquer_complets'),
        )
