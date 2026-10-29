# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget
from core.forms.base import FormulaireBase
from core.forms.accordeon import Accordeon, Section
from core.models import Depot


class Formulaire(FormulaireBase, forms.Form):
    type_selection = forms.ChoiceField(label="Type de sélection", choices=[
        ("DATE_DEPOT", "Les dépôts d'une période"),
        ("SELECTION", "Sélection de dépôts"),
        ("PRESTATIONS", "Les prestations ventilées sur une période"),
    ], initial="DATE_DEPOT", required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    depots = forms.ModelMultipleChoiceField(label="Dépôts", required=False, queryset=Depot.objects.all().order_by("date"), help_text="Utilisez CTRL ou SHIFT pour sélectionner plusieurs dépôts.")
    filtre_activites = forms.BooleanField(label="Uniquement les prestations rattachées aux activités suivantes", initial=False, required=False)
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    regroupement_colonne = forms.ChoiceField(label="Colonne", choices=[("mois", "Mois"), ("annee", "Année")], initial="mois", required=False)
    afficher_detail = forms.BooleanField(label="Afficher le détail des prestations", initial=True, required=False)
    afficher_date_depot = forms.BooleanField(label="Afficher la date du dépôt", initial=True, required=False)
    afficher_montant_depot = forms.BooleanField(label="Afficher le montant du dépôt", initial=True, required=False)
    afficher_code_compta = forms.BooleanField(label="Afficher le code comptable du dépôt", initial=True, required=False)
    afficher_code_compta_prestations = forms.BooleanField(label="Afficher le code comptable des prestations", initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.fields["depots"].widget.attrs = {"style": "height:250px"}

        self.helper.layout = Layout(
            Accordeon(
                Section("Données",
                    Field("type_selection"),
                    Field("periode"),
                    Field("depots"),
                    Field("filtre_activites"),
                    Field("activites"),
                    icone="fa-database",
                ),
                Section("Options",
                    Field("regroupement_colonne"),
                    Field("afficher_detail"),
                    Field("afficher_date_depot"),
                    Field("afficher_montant_depot"),
                    Field("afficher_code_compta"),
                    Field("afficher_code_compta_prestations"),
                    icone="fa-sliders",
                ),
                css_id="accordeon_detail_ventilations_depots",
            ),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        if self.cleaned_data.get("type_selection") == "PRESTATIONS" and self.cleaned_data.get("filtre_activites"):
            selection = json.loads(self.cleaned_data.get("activites") or "{}")
            if selection.get("type") != "toutes" and not selection.get("ids"):
                self.add_error("activites", "Vous n'avez sélectionné aucune activité")
        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_type_selection() {
        var type_selection = $("#id_type_selection").val();
        $('#div_id_periode').toggle(type_selection != 'SELECTION');
        $('#div_id_depots').toggle(type_selection == 'SELECTION');
        $('#div_id_filtre_activites').toggle(type_selection == 'PRESTATIONS');
        $('#div_id_activites').toggle(type_selection == 'PRESTATIONS' && $("#id_filtre_activites").is(":checked"));
    }
    $(document).ready(function() {
        $('#id_type_selection, #id_filtre_activites').on('change', On_change_type_selection);
        On_change_type_selection.call($('#id_type_selection').get(0));
    });
</script>
"""
