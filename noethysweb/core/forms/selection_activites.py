# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.widgets import SelectionActivitesWidget
from core.forms.base import FormulaireBase
import json


class Formulaire(FormulaireBase, forms.Form):
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": True}))

    def __init__(self, *args, **kwargs):
        defaut = kwargs.pop("defaut", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_selection_activites'
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False

        if defaut:
            self.fields["activites"].initial = json.dumps(defaut)

        self.helper.layout = Layout(
            Field('activites'),
        )
