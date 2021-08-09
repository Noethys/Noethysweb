# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import TypeMaladie
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = TypeMaladie
        fields = "__all__"
        widgets = {
            'vaccin_date_naiss_min': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'types_maladies_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_maladies_liste' %}"),
            Fieldset("Généralités",
                Field('nom'),
            ),
            Fieldset("Vaccination",
                Field('vaccin_obligatoire'),
                Field('vaccin_date_naiss_min'),
            ),
            HTML(EXTRA_HTML),
        )


EXTRA_HTML = """
<script>

// Vaccin obligatoire
function On_change_vaccin_obligatoire() {
    $('#div_id_vaccin_date_naiss_min').hide();
    if ($(this).prop("checked")) {
        $('#div_id_vaccin_date_naiss_min').show();
    };
}
$(document).ready(function() {
    $('#id_vaccin_obligatoire').on('change', On_change_vaccin_obligatoire);
    On_change_vaccin_obligatoire.call($('#id_vaccin_obligatoire').get(0));
});

</script>
"""
