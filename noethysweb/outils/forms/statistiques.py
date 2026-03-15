# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget
from core.models import Vacance, TypeCotisation, LISTE_VACANCES, LISTE_MOIS, LISTE_ETATS_CONSO
from core.forms.select2 import Select2MultipleWidget
from core.forms.base import FormulaireBase


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
            ("familles_qf", "Quotients familiaux des familles"),
        )),
        ("Consommations", (
            ("consommations_saisie", "Saisie des consommations"),
        )),
    ]
    rubriques = forms.MultipleChoiceField(label="Rubriques", choices=choix_rubrique, required=True, help_text="Sélectionnez une ou plusieurs rubriques.")
    choix_condition = [
        ("INSCRITS", "Inscrits"),
        ("INSCRITS_PERIODE", "Inscrits sur une période de dates"),
        ("ANNEE", "Présents sur une année"),
        ("MOIS", "Présents sur un mois"),
        ("VACANCES", "Présents sur une période de vacances"),
        ("PERIODE", "Présents sur une période de dates"),
        ("ADHERENTS_PERIODE", "Adhérents sur une période de dates"),
    ]
    condition = forms.TypedChoiceField(label="Condition", choices=choix_condition, initial="INSCRITS", required=True)
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    vacances = forms.ChoiceField(label="Vacances", choices=LISTE_VACANCES, required=False)
    mois = forms.ChoiceField(label="Mois", choices=LISTE_MOIS, required=False)
    annee = forms.IntegerField(label="Année", required=False, initial=datetime.date.today().year)
    periode = forms.CharField(label="Période", required=False, widget=DateRangePickerWidget())
    tranches_qf = forms.CharField(label="Tranches de QF", required=False, help_text="Saisissez les tranches à étudier de la façon suivante : 0-500;501-1000;etc...")
    etats = forms.MultipleChoiceField(required=False, widget=Select2MultipleWidget(), choices=LISTE_ETATS_CONSO, initial=["reservation", "present"])
    types_cotisations = forms.ModelMultipleChoiceField(label="Types d'adhésions", queryset=TypeCotisation.objects.all().order_by("nom"), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_statistiques'
        self.helper.form_method = 'post'

        # Types de cotisations
        self.fields["types_cotisations"].initial = TypeCotisation.objects.all()

        self.helper.layout = Layout(
            Field("rubriques"),
            Field("tranches_qf"),
            Field("condition"),
            Field("activites"),
            Field("vacances"),
            Field("mois"),
            Field("annee"),
            Field("periode"),
            Field("etats"),
            Field("types_cotisations"),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        if self.cleaned_data["condition"] == "VACANCES":
            if not Vacance.objects.filter(nom=self.cleaned_data["vacances"], annee=self.cleaned_data["annee"]).exists():
                self.add_error("vacances", "La période de vacances sélectionnée n'a pas été paramétrée")
                return

        return self.cleaned_data



EXTRA_SCRIPT = """
<script>

// Rubriques
function On_change_rubriques() {
    $('#div_id_tranches_qf').hide();
    if (jQuery.inArray("familles_qf", $(this).val()) != -1) {
        $('#div_id_tranches_qf').show();
    };
}
$(document).ready(function() {
    $('#id_rubriques').change(On_change_rubriques);
    On_change_rubriques.call($('#id_rubriques').get(0));
});

// Données
function On_change_condition() {
    $('#div_id_activites').hide();
    $('#div_id_vacances').hide();
    $('#div_id_mois').hide();
    $('#div_id_annee').hide();
    $('#div_id_periode').hide();
    $('#div_id_etats').hide();
    $('#div_id_types_cotisations').hide();
    if ($(this).val() == 'INSCRITS') {
        $('#div_id_activites').show();
    };
    if ($(this).val() == 'INSCRITS_PERIODE') {
        $('#div_id_activites').show();
        $('#div_id_periode').show();
    };
    if ($(this).val() == 'VACANCES') {
        $('#div_id_activites').show();
        $('#div_id_vacances').show();
        $('#div_id_annee').show();
        $('#div_id_etats').show();
    };
    if ($(this).val() == 'MOIS') {
        $('#div_id_activites').show();
        $('#div_id_mois').show();
        $('#div_id_annee').show();
        $('#div_id_etats').show();
    };
    if ($(this).val() == 'ANNEE') {
        $('#div_id_activites').show();
        $('#div_id_annee').show();
        $('#div_id_etats').show();
    };
    if ($(this).val() == 'PERIODE') {
        $('#div_id_activites').show();
        $('#div_id_periode').show();
        $('#div_id_etats').show();
    };
    if ($(this).val() == 'ADHERENTS_PERIODE') {
        $('#div_id_periode').show();
        $('#div_id_types_cotisations').show();
    };
}
$(document).ready(function() {
    $('#id_condition').change(On_change_condition);
    On_change_condition.call($('#id_condition').get(0));
});

</script>
"""