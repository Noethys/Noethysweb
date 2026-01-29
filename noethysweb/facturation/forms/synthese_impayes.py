# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    type_activites = forms.ChoiceField(label="Activités", choices=[("TOUTES", "Toutes les activités"), ("SELECTION", "Les activités suivantes")], initial="TOUTES", required=False)
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    regroupement_lignes = forms.ChoiceField(label="Lignes", choices=[("activites", "Activité"), ("familles", "Famille")], initial="activites", required=False)
    regroupement_colonnes = forms.ChoiceField(label="Colonnes", choices=[("mois", "Mois"), ("annee", "Année")], initial="mois", required=False)
    afficher_detail = forms.BooleanField(label="Afficher la ligne de détail", initial=True, required=False)
    donnees = forms.MultipleChoiceField(label="Type de prestation", required=True, widget=Select2MultipleWidget(), choices=[("cotisation", "Cotisations"), ("consommation", "Consommations"), ("location", "Locations"), ("autre", "Autres")], initial=["cotisation", "consommation", "location", "autre"])
    filtre_reglements_saisis = forms.CharField(label="Règlements saisis sur une période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    filtre_reglements_deposes = forms.CharField(label="Règlements déposés sur une période", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    uniquement_prestations_facturees = forms.BooleanField(label="Uniquement les prestations facturées", initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Fieldset("Données",
                Field('periode'),
                Field('type_activites'),
                Field('activites'),
            ),
            Fieldset("Affichage",
                Field('regroupement_lignes'),
                Field('afficher_detail'),
                Field('regroupement_colonnes'),
            ),
            Fieldset("Filtres",
                Field('donnees'),
                Field('uniquement_prestations_facturees'),
                Field('filtre_reglements_saisis'),
                Field('filtre_reglements_deposes'),
            ),
            HTML(EXTRA_HTML),
        )


EXTRA_HTML = """
<script>
    function On_change_type_activites() {
        $('#div_id_activites').hide();
        if ($("#id_type_activites").val() == 'SELECTION') {
            $('#div_id_activites').show();
        };
    }
    $(document).ready(function() {
        $('#id_type_activites').on('change', On_change_type_activites);
        On_change_type_activites.call($('#id_type_activites').get(0));
    });
</script>
"""
