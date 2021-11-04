# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=False, widget=DateRangePickerWidget(attrs={"auto_application": True, "afficher_periodes_predefinies": False}))
    choix_frequence = [("0", "Toutes les semaines"), ("1", "Une semaine sur deux"), ("2", "Semaines paires/impaires")]
    frequence = forms.TypedChoiceField(label="Fréquence", choices=choix_frequence, initial="0", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'grille_appliquer_semaine_type'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Row(
                Column("periode", css_class="form-group col-md-6 mb-0"),
                Column("frequence", css_class="form-group col-md-6 mb-0"),
                css_class='form-row'
            ),
        )
