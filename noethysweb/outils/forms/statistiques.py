# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget, DatePickerWidget, MonthPickerWidget
from core.models import Vacance, LISTE_VACANCES, LISTE_MOIS
from django_select2.forms import Select2Widget
from core.forms.base import FormulaireBase
import datetime


class Formulaire(FormulaireBase, forms.Form):
    choix_rubrique = [
        ("Individus", (
            ("individus_nombre", "Nombre d'individus"),
            ("individus_genre", "Genre des individus"),
            ("individus_age", "Age des individus"),
            ("individus_coordonnees", "Coordonnées des individus"),
            ("individus_scolarite", "Scolarité des individus"),
            ("individus_profession", "Profession des individus"),
        )),
        ("Familles", (
            ("familles_nombre", "Nombre de familles"),
            ("familles_caisse", "Caisse des familles"),
            ("familles_composition", "Composition des familles"),
        )),
        ("Consommations", (
            ("consommations_saisie", "Saisie des consommations"),
        )),
    ]
    rubrique = forms.ChoiceField(label="Rubrique", widget=Select2Widget({"lang": "fr", "data-width": "100%"}), choices=choix_rubrique, required=True)
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    choix_donnees = [("INSCRITS", "Inscrits"), ("ANNEE", "Présents sur une année"), ("MOIS", "Présents sur un mois"),
                     ("VACANCES", "Présents sur une période de vacances"), ("PERIODE", "Présents sur une période de dates")]
    donnees = forms.TypedChoiceField(label="Données", choices=choix_donnees, initial="INSCRITS", required=True)
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
            Field('rubrique'),
            Field('activites'),
            Field('donnees'),
            Field('vacances'),
            Field('mois'),
            Field('annee'),
            Field('periode'),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        if self.cleaned_data["donnees"] == "VACANCES":
            if not Vacance.objects.filter(nom=self.cleaned_data["vacances"], annee=self.cleaned_data["annee"]).exists():
                self.add_error("vacances", "La période de vacances sélectionnée n'a pas été paramétrée")
                return

        return self.cleaned_data



EXTRA_SCRIPT = """
<script>

// Données
function On_change_donnees() {
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
    $('#id_donnees').change(On_change_donnees);
    On_change_donnees.call($('#id_donnees').get(0));
});

</script>
"""