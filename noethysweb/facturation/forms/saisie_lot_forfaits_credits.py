# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, Select_activite
from core.models import Activite, Tarif
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période du forfait", required=True, widget=DateRangePickerWidget())
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)
    tarif = forms.ModelChoiceField(label="Forfait à appliquer", queryset=Tarif.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request

        self.helper.layout = Layout(
            Field("periode"),
            Field("activite"),
            Field("tarif"),
            HTML(EXTRA_SCRIPT),
        )

EXTRA_SCRIPT = """
<script>

{% include 'core/csrftoken.html' %}

// Actualise la liste des tarifs en fonction de l'activité sélectionnée
function Maj_tarifs() {
    var idactivite = $("#id_activite").val();
    var periode = $("#id_periode").val(); 
    var idtarif = $("#id_tarif").val(); 
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_saisie_lot_forfaits_credits_get_tarifs' %}",
        data: {
            "idactivite": idactivite,
            "periode": periode
        },
        success: function (data) { 
            $("#id_tarif").html(data);
            $("#id_tarif").val(idtarif);
            if (data == '') {
                $("#div_id_tarif").hide()
            } else {
                $("#div_id_tarif").show()
            }
        }
    });
};
$(document).ready(function() {
    $('#id_activite').change(Maj_tarifs);
    $('#id_periode').change(Maj_tarifs);
    Maj_tarifs.call($('#id_activite').get(0));
});

</script>

"""
