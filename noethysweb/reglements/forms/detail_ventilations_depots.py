# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase
from core.models import Depot


class Formulaire(FormulaireBase, forms.Form):
    type_selection = forms.ChoiceField(label="Type de sélection", choices=[("DATE_DEPOT", "Les dépôts d'une période"), ("SELECTION", "Sélection de dépôts")], initial="DATE_DEPOT", required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    depots = forms.ModelMultipleChoiceField(label="Dépôts", required=False, queryset=Depot.objects.all().order_by("date"), help_text="Utilisez CTRL ou SHIFT pour sélectionner plusieurs dépôts.")
    regroupement_colonne = forms.ChoiceField(label="Colonne", choices=[("mois", "Mois"), ("annee", "Année")], initial="mois", required=False)
    afficher_detail = forms.BooleanField(label="Afficher le détail des prestations", initial=True, required=False)
    afficher_date_depot = forms.BooleanField(label="Afficher la date du dépôt", initial=True, required=False)
    afficher_montant_depot = forms.BooleanField(label="Afficher le montant du dépôt", initial=True, required=False)
    afficher_code_compta = forms.BooleanField(label="Afficher le code comptable du dépôt", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.fields["depots"].widget.attrs = {"style": "height:250px"}

        self.helper.layout = Layout(
            Fieldset("Données",
                Field("type_selection"),
                Field("periode"),
                Field("depots"),
            ),
            Fieldset("Options",
                Field("regroupement_colonne"),
                Field("afficher_detail"),
                Field("afficher_date_depot"),
                Field("afficher_montant_depot"),
                Field("afficher_code_compta"),
            ),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<script>
    function On_change_type_selection() {
        $('#div_id_periode').hide();
        $('#div_id_depots').hide();
        if ($("#id_type_selection").val() == 'DATE_DEPOT') {
            $('#div_id_periode').show();
        };
        if ($("#id_type_selection").val() == 'SELECTION') {
            $('#div_id_depots').show();
        };
    }
    $(document).ready(function() {
        $('#id_type_selection').on('change', On_change_type_selection);
        On_change_type_selection.call($('#id_type_selection').get(0));
    });
</script>
"""
