# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, forms.Form):
    # Date de début
    choix_date_debut = forms.TypedChoiceField(label="Date de début de validité", choices=[("PAS_MODIFIER", "Ne pas modifier"), ("MODIFIER", "Appliquer une date de début")], initial="PAS_MODIFIER", required=False)
    date_debut = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget())

    # date de fin
    choix_date_fin = forms.TypedChoiceField(label="Date de fin de validité", choices=[("PAS_MODIFIER", "Ne pas modifier"), ("ILLIMITEE", "Appliquer une durée illimitée"), ("LIMITEE", "Appliquer une date de fin")], initial="PAS_MODIFIER", required=False)
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget())

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'piece_modifier_form'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Date de début",
                Field("choix_date_debut"),
                Field("date_debut"),
            ),
            Fieldset("Date de fin",
                Field("choix_date_fin"),
                Field("date_fin"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Vérifie si au moins une modification a été sélectionnée
        if self.cleaned_data["choix_date_debut"] == "PAS_MODIFIER" and self.cleaned_data["choix_date_fin"] == "PAS_MODIFIER":
            self.add_error("choix_date_debut", "Vous n'avez sélectionné aucune modification à appliquer")
            return

        # Date de début
        if self.cleaned_data["choix_date_debut"] == "MODIFIER" and not self.cleaned_data["date_debut"]:
            self.add_error("date_debut", "Vous devez saisir une date de début")
            return

        # Date de fin
        if self.cleaned_data["choix_date_fin"] != "PAS_MODIFIER":
            if self.cleaned_data["choix_date_fin"] == "ILLIMITEE":
                self.cleaned_data["date_fin"] = datetime.date(2999, 1, 1)
            else:
                if not self.cleaned_data["date_fin"]:
                    self.add_error("date_fin", "Vous devez saisir une date de fin")
                    return

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

    // Choix date début
    function On_change_choix_date_debut() {
        $('#div_id_date_debut').hide();
        if ($('#id_choix_date_debut').val() == 'MODIFIER') {
            $('#div_id_date_debut').show();
        }
    }
    $(document).ready(function() {
        $('#id_choix_date_debut').change(On_change_choix_date_debut);
        On_change_choix_date_debut.call($('#id_choix_date_debut').get(0));
    });

    // Choix date fin
    function On_change_choix_date_fin() {
        $('#div_id_date_fin').hide();
        if ($('#id_choix_date_fin').val() == 'LIMITEE') {
            $('#div_id_date_fin').show();
        }
    }
    $(document).ready(function() {
        $('#id_choix_date_fin').change(On_change_choix_date_fin);
        On_change_choix_date_fin.call($('#id_choix_date_fin').get(0));
    });

</script>
"""
