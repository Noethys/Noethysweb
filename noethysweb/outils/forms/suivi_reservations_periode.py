# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    choix_historique = [
        (3, "3 heures"),(6, "6 heures"),(12, "12 heures"),(24, "24 heures"),(48, "48 heures"), (72, "3 jours"),(120, "5 jours"),
        (168, "1 semaine"),(336, "2 semaines"), (720, "1 mois"),(2160, "3 mois"),(4320, "6 mois"),
    ]
    periode_historique = forms.ChoiceField(label="Période de l'historique à afficher", choices=choix_historique, initial=12, required=False)
    filtrage = forms.ChoiceField(label="Afficher les réservations d'une période donnée", choices=[("NON", "Non"), ("DATES", "Uniquement la période suivante")], initial="NON", required=False)
    periode_reservations = forms.CharField(label="Période des réservations", required=False, widget=DateRangePickerWidget())

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_periode_reservations_parametres'
        self.helper.form_method = 'post'

        periode_reservations_initial = self.initial.get("periode_reservations", "NON")
        if periode_reservations_initial and periode_reservations_initial != "None":
            self.fields["filtrage"].initial = "DATES"

        # Affichage
        self.helper.layout = Layout(
            Field("periode_historique"),
            Field("filtrage"),
            Field("periode_reservations"),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        if self.cleaned_data["filtrage"] == "NON":
            self.cleaned_data["periode_reservations"] = None
        return self.cleaned_data

EXTRA_HTML = """
<script>

    function On_change_filtrage() {
        $('#div_id_periode_reservations').hide();
        if ($("#id_filtrage").val() == 'DATES') {
            $('#div_id_periode_reservations').show();
        };
    }
    $(document).ready(function() {
        $('#id_filtrage').on('change', On_change_filtrage);
        On_change_filtrage.call($('#id_filtrage').get(0));
    });

</script>
"""
