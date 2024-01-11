# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, forms.Form):
    date_situation = forms.DateField(label="Date de situation", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=True)
    afficher_debits = forms.BooleanField(label="Afficher les soldes débiteurs", required=False, initial=True)
    afficher_credits = forms.BooleanField(label="Afficher les soldes créditeurs", required=False, initial=True)
    afficher_nuls = forms.BooleanField(label="Afficher les soldes nuls", required=False, initial=True)
    uniquement_factures = forms.BooleanField(label="Uniquement les prestations facturées", required=False, initial=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Date de situation
        self.fields["date_situation"].initial = datetime.date.today()

        self.helper.layout = Layout(
            Field("date_situation"),
            Field("afficher_debits"),
            Field("afficher_credits"),
            Field("afficher_nuls"),
            Field("uniquement_factures"),
        )
