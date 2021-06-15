# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column, Fieldset, Div
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Depot, Reglement
from core.widgets import DatePickerWidget
from reglements.widgets import Reglements_depot
import datetime


class Formulaire(FormulaireBase, ModelForm):
    nom = forms.CharField(label="Nom du dépôt", required=True)
    date = forms.DateField(label="Date de dépôt", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    verrouillage = forms.BooleanField(label="Verrouillage du dépôt", initial=False, required=False)
    observations = forms.CharField(label="Observations", widget=forms.Textarea(attrs={'rows': 3}), required=False)
    reglements = forms.CharField(label="Règlements", required=False, widget=Reglements_depot())

    class Meta:
        model = Depot
        fields = ["nom", "date", "compte", "code_compta", "observations", "verrouillage"]

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'depots_reglements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affiche le résumé des règlements inclus
        if self.instance.pk:
            reglements = Reglement.objects.filter(depot=self.instance.pk)
            self.fields['reglements'].initial = ";".join([str(reglement.pk) for reglement in reglements])

        if not self.instance.pk:
            self.fields['date'].initial = datetime.date.today()

            # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'depots_reglements_liste' %}"),
            Field('nom'),
            Field('date'),
            Field('compte'),
            Field('code_compta'),
            Field('observations'),
            Field('reglements'),
            Field('verrouillage'),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<script>

// Verrouillage
function On_change_verrouillage() {
    $('#bouton_modifier_reglements').hide();
    if (!($(this).prop("checked"))) {
        $('#bouton_modifier_reglements').show();
    };
}
$(document).ready(function() {
    $('#id_verrouillage').on('change', On_change_verrouillage);
    On_change_verrouillage.call($('#id_verrouillage').get(0));
});

</script>
"""