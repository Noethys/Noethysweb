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
from core.models import TypeQuotient
import datetime


class Formulaire(FormulaireBase, forms.Form):
    type_quotient = forms.ModelChoiceField(label="Type de quotient", queryset=TypeQuotient.objects.all(), required=True)
    date = forms.DateField(label="Date de situation", required=True, widget=DatePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    presents = forms.CharField(label="Uniquement les présents", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    familles = forms.ChoiceField(label="Familles", choices=[("TOUTES", "Toutes les familles"), ("AVEC_QF", "Uniquement les familles avec QF"), ("SANS_QF", "Uniquement les familles sans QF")], required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.fields['date'].initial = datetime.date.today()

        self.helper.layout = Layout(
            Field('activites'),
            Field('presents'),
            Field('date'),
            Field('type_quotient'),
            Field('familles'),
        )
