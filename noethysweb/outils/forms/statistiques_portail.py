# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget
from core.models import Vacance, LISTE_VACANCES, LISTE_MOIS
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    choix_rubrique = [
        ("connexions", "Connexions"),
        ("renseignements", "Renseignements"),
        ("reservations", "Réservations"),
    ]
    rubriques = forms.MultipleChoiceField(label="Rubriques", choices=choix_rubrique, required=True, help_text="Sélectionnez une ou plusieurs rubriques.")
    choix_periodes = [
        ("ANNEE", "Année"),
        ("MOIS", "Mois"),
        ("VACANCES", "Période de vacances"),
        ("PERIODE", "Période de dates"),
    ]
    type_periode = forms.TypedChoiceField(label="Type de période", choices=choix_periodes, initial="INSCRITS", required=True)
    vacances = forms.ChoiceField(label="Vacances", choices=LISTE_VACANCES, required=False)
    mois = forms.ChoiceField(label="Mois", choices=LISTE_MOIS, required=False)
    annee = forms.IntegerField(label="Année", required=False, initial=datetime.date.today().year)
    periode = forms.CharField(label="Période", required=False, widget=DateRangePickerWidget())

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_statistiques'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Field('rubriques'),
            Field('type_periode'),
            Field('vacances'),
            Field('mois'),
            Field('annee'),
            Field('periode'),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        if self.cleaned_data["type_periode"] == "VACANCES":
            if not Vacance.objects.filter(nom=self.cleaned_data["vacances"], annee=self.cleaned_data["annee"]).exists():
                self.add_error("vacances", "La période de vacances sélectionnée n'a pas été paramétrée")
                return

        return self.cleaned_data



EXTRA_SCRIPT = """
<script>

// Données
function On_change_type_periode() {
    $('#div_id_vacances').hide();
    $('#div_id_mois').hide();
    $('#div_id_annee').hide();
    $('#div_id_periode').hide();
    if($(this).val() == 'VACANCES') {
        $('#div_id_vacances').show();
        $('#div_id_annee').show();
    };
    if($(this).val() == 'MOIS') {
        $('#div_id_mois').show();
        $('#div_id_annee').show();
    };
    if($(this).val() == 'ANNEE') {
        $('#div_id_annee').show();
    };
    if($(this).val() == 'PERIODE') {
        $('#div_id_periode').show();
    };
}
$(document).ready(function() {
    $('#id_type_periode').change(On_change_type_periode);
    On_change_type_periode.call($('#id_type_periode').get(0));
});

</script>
"""