# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML
from crispy_forms.bootstrap import Field
from django_select2.forms import Select2Widget
from core.forms.select2 import Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.widgets import DateRangePickerWidget
from core.models import Famille, ModeReglement


class Formulaire(FormulaireBase, forms.Form):
    type_selection = forms.ChoiceField(label="Type de sélection", choices=[("DATE_SAISIE", "Les règlements saisis sur une période"),
                                                                           ("DATE_DEPOT", "Les règlements déposés sur une période"),
                                                                           ("FAMILLE", "Les règlements d'une famille"),],
                                       initial="DATE_SAISIE", required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget(), queryset=Famille.objects.all().order_by("nom"), required=False)
    regroupement_colonne = forms.ChoiceField(label="Colonne", choices=[("mois", "Mois"), ("annee", "Année"), ("nom_activite", "Nom de l'activité"),
                                                                       ("code_comptable", "Code comptable"), ("code_analytique", "Code analytique")], initial="mois", required=False)
    afficher_detail = forms.BooleanField(label="Afficher le détail des prestations", initial=True, required=False)
    afficher_id = forms.BooleanField(label="Afficher le ID du règlement", initial=True, required=False)
    afficher_date = forms.BooleanField(label="Afficher la date du règlement", initial=True, required=False)
    afficher_mode = forms.BooleanField(label="Afficher le mode du règlement", initial=True, required=False)
    afficher_famille = forms.BooleanField(label="Afficher la famille du règlement", initial=True, required=False)
    afficher_montant = forms.BooleanField(label="Afficher le montant du règlement", initial=True, required=False)
    filtre_modes = forms.TypedChoiceField(label="Filtre sur les modes", choices=[("TOUS", "Tous les modes"), ("SELECTION", "Uniquement les modes sélectionnés")], initial="TOUS", required=False)
    selection_modes = forms.ModelMultipleChoiceField(label="Sélection de modes", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), queryset=ModeReglement.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Fieldset("Données",
                Field("type_selection"),
                Field("periode"),
                Field("famille"),
            ),
            Fieldset("Options",
                Field("regroupement_colonne"),
                Field("afficher_detail"),
                Field("afficher_id"),
                Field("afficher_date"),
                Field("afficher_mode"),
                Field("afficher_famille"),
                Field("afficher_montant"),
            ),
            Fieldset("Filtres",
                Field("filtre_modes"),
                Field("selection_modes"),
            ),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<script>
    function On_change_type_selection() {
        $('#div_id_periode').hide();
        $('#div_id_famille').hide();
        if ($("#id_type_selection").val() == 'DATE_SAISIE') {
            $('#div_id_periode').show();
        };
        if ($("#id_type_selection").val() == 'DATE_DEPOT') {
            $('#div_id_periode').show();
        };
        if ($("#id_type_selection").val() == 'FAMILLE') {
            $('#div_id_famille').show();
        };
    }
    $(document).ready(function() {
        $('#id_type_selection').on('change', On_change_type_selection);
        On_change_type_selection.call($('#id_type_selection').get(0));
    });
    
    function On_change_filtre_modes() {
        $('#div_id_selection_modes').hide();
        if ($("#id_filtre_modes").val() == 'SELECTION') {
            $('#div_id_selection_modes').show();
        };
    }
    $(document).ready(function() {
        $('#id_filtre_modes').on('change', On_change_filtre_modes);
        On_change_filtre_modes.call($('#id_filtre_modes').get(0));
    });

</script>
"""
