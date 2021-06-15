# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, TabHolder, Tab
from core.forms.base import FormulaireBase
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, forms.Form):
    date = forms.CharField(label="Date", required=True, widget=DatePickerWidget(attrs={'multidate': True, 'affichage_inline': True}))
    multidate = forms.BooleanField(label="Activer la sélection multiple", required=False, initial=False)

    def __init__(self, *args, **kwargs):
        dates = kwargs.pop("dates", [])
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_date'
        self.helper.form_method = 'post'

        # Pour permettre la récupération de forms multiples
        self.helper.form_tag = False

        # Valeurs initiales
        self.fields['date'].label = False
        self.fields["date"].initial = ";".join([str(date) for date in dates])

        # Affichage
        self.helper.layout = Layout(
            Field('date'),
            Field('multidate'),
            HTML(EXTRA_HTML),
            HTML("""<button type="submit" name="appliquer_date" class="btn btn-default btn-block btn-sm" style="margin-top: -5px;" title="Appliquer">Appliquer</button>"""),
        )


EXTRA_HTML = """
<script>

    // Activation du multidates
    function On_change_multidate() {
        multidate = $(this).prop("checked");
        $(".datepickerwidget").datepicker('destroy');
        init_datepicker();
    }
    $(document).ready(function() {
        $('#id_multidate').on('change', On_change_multidate);
        On_change_multidate.call($('#id_multidate').get(0));
    });

</script>
"""