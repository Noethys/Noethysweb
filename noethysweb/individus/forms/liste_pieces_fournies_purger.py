# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget


class Formulaire_purge(FormulaireBase, forms.Form):
    purger_perimees = forms.BooleanField(label="Supprimer les pièces périmées depuis le", required=False)
    date_perimees = forms.DateField(label="", required=False, widget=DatePickerWidget())
    purger_remplacees = forms.BooleanField(label="Supprimer les pièces remplacées par une pièce plus récente de même type pour le même individu/famille", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire_purge, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_purge_pieces"
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-trash-o margin-r-5'></i>Purger", ajouter=False, annuler_url="{% url 'liste_pieces_fournies' %}"),
            Fieldset("Critères de purge",
                Field('purger_perimees'),
                Div(Field('date_perimees'), style="margin-left: 20px;"),
                Field('purger_remplacees'),
            ),
        )

    def clean(self):
        if not self.cleaned_data.get("purger_perimees") and not self.cleaned_data.get("purger_remplacees"):
            raise forms.ValidationError("Vous devez sélectionner au moins un critère de purge.")
        if self.cleaned_data.get("purger_perimees") and not self.cleaned_data.get("date_perimees"):
            self.add_error("date_perimees", "Vous devez saisir une date de référence.")
        return self.cleaned_data
