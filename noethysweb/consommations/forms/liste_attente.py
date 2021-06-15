# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, Profil_configuration
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    donnees = forms.ChoiceField(label="Données", choices=[("periode_reference", "Utiliser la période de référence"), ("periode_definie", "Utiliser les paramètres ci-dessous")], initial="periode_reference", required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Field('donnees'),
            Field('periode'),
            Field('activites'),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<script>

    function On_change_donnees() {
        var etat = ($('#id_donnees').val() == 'periode_reference');
        $('#div_id_periode').prop('hidden', etat);
        $('#div_id_activites').prop('hidden', etat);
    }
    $(document).ready(function() {
        $('#id_donnees').change(On_change_donnees);
        On_change_donnees.call($('#id_donnees').get(0));
    });

</script>
"""