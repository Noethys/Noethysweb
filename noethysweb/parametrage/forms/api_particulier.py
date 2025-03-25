# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    token = forms.CharField(label="Quel est votre token API Particulier ?", widget=forms.Textarea(attrs={"rows": 3}), required=True, help_text="Copiez-collez le token qui est consultable sur votre compte API Particulier.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_api_particulier"
        self.helper.form_method = "post"

        # Affichage
        self.helper.layout = Layout(
            Field("token"),
        )

    def clean(self):
        if len(self.cleaned_data.get("token", "")) < 10:
            self.add_error("token", "Le nombre de caractères ne semble pas suffisant.")
        return self.cleaned_data
