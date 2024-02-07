# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget, DatePickerWidget
from core.models import TypeQuotient


class Formulaire(FormulaireBase, forms.Form):
    familles = forms.ChoiceField(label="Familles", choices=[("TOUTES", "Toutes les familles"), ("SELECTION", "Une sélection de familles")], required=True)
    type_quotient = forms.ModelChoiceField(label="Type de quotient", queryset=TypeQuotient.objects.all(), required=True)
    date = forms.DateField(label="Date de situation", required=True, widget=DatePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"id": 2, "afficher_colonne_detail": False}))
    presents = forms.CharField(label="Uniquement les présents", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    filtre = forms.ChoiceField(label="Filtre", choices=[("TOUTES", "Familles avec ou sans QF"), ("AVEC_QF", "Uniquement les familles avec QF"), ("SANS_QF", "Uniquement les familles sans QF")], required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.fields['date'].initial = datetime.date.today()

        self.helper.layout = Layout(
            Field('familles'),
            Field('activites'),
            Field('presents'),
            Field('date'),
            Field('type_quotient'),
            Field('filtre'),
            HTML(EXTRA_HTML),
        )


EXTRA_HTML = """
<script>
    function On_change_familles() {
        $('#div_id_activites').hide();
        $('#div_id_presents').hide();
        if ($("#id_familles").val() == "SELECTION") {
            $('#div_id_activites').show();
            $('#div_id_presents').show();
        };
    }
    $(document).ready(function() {
        $('#id_familles').change(On_change_familles);
        On_change_familles.call($('#id_familles').get(0));
    });
</script>
"""
