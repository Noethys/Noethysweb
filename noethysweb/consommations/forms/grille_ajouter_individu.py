# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from django_select2.forms import HeavySelect2MultipleWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    individu = forms.MultipleChoiceField(label="Recherchez les individus à ajouter", widget=HeavySelect2MultipleWidget({"lang": "fr", "data-width": "100%", "data-ajax--type": "GET"}, data_url="get_individus"), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'grille_ajouter_individu'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Field("individu"),
        )
