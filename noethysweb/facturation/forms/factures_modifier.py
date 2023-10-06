# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import LotFactures, FactureRegie, PrefixeFacture
from core.widgets import DatePickerWidget, Select_avec_commandes


class Formulaire(FormulaireBase, forms.Form):
    modifier_date_edition = forms.BooleanField(label="Modifier la date d'émission", required=False)
    date_edition = forms.DateField(label="Date d'émission", required=False, widget=DatePickerWidget())
    modifier_date_echeance = forms.BooleanField(label="Modifier la date d'échéance", required=False)
    date_echeance = forms.DateField(label="Date d'échéance", required=False, widget=DatePickerWidget())
    modifier_lot = forms.BooleanField(label="Modifier le lot", required=False)
    lot = forms.ModelChoiceField(label="Lot de factures", queryset=LotFactures.objects.all(), required=False, widget=Select_avec_commandes(
                      {"donnees_extra": {}, "url_ajax": "ajax_modifier_lot_factures",
                       "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot de factures", "modifier": "Modifier un lot de factures"}}))
    modifier_regie = forms.BooleanField(label="Modifier la régie", required=False)
    regie = forms.ModelChoiceField(label="Régie", queryset=FactureRegie.objects.all(), required=False)
    modifier_prefixe = forms.BooleanField(label="Modifier le préfixe", required=False)
    prefixe = forms.ModelChoiceField(label="Préfixe", queryset=PrefixeFacture.objects.all(), required=False)
    modifier_date_limite_paiement = forms.BooleanField(label="Modifier la date limite de paiement en ligne", required=False)
    date_limite_paiement = forms.DateField(label="Date limite paiement en ligne", required=False, widget=DatePickerWidget())

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'options_facture'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Nouveaux paramètres des factures",
                Field('modifier_date_edition'),
                Field('date_edition'),
                Field('modifier_date_echeance'),
                Field('date_echeance'),
                Field('modifier_date_limite_paiement'),
                Field('date_limite_paiement'),
                Field('modifier_prefixe'),
                Field('prefixe'),
                Field('modifier_lot'),
                Field('lot'),
                Field('modifier_regie'),
                Field('regie'),
            ),
            Fieldset("Sélection des factures à modifier"),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Date édition
        if self.cleaned_data["modifier_date_edition"] and not self.cleaned_data["date_edition"]:
            self.add_error('modifier_edition', "Vous devez renseigner la date d'édition souhaitée")
            return

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Date édition
function On_change_date_edition() {
    $('#div_id_date_edition').hide();
    if ($(this).prop("checked")) {
        $('#div_id_date_edition').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_date_edition').change(On_change_date_edition);
    On_change_date_edition.call($('#id_modifier_date_edition').get(0));
});

// Date échéance
function On_change_date_echeance() {
    $('#div_id_date_echeance').hide();
    if ($(this).prop("checked")) {
        $('#div_id_date_echeance').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_date_echeance').change(On_change_date_echeance);
    On_change_date_echeance.call($('#id_modifier_date_echeance').get(0));
});

// Date limite de paiement en ligne
function On_change_date_limite_paiement() {
    $('#div_id_date_limite_paiement').hide();
    if ($(this).prop("checked")) {
        $('#div_id_date_limite_paiement').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_date_limite_paiement').change(On_change_date_limite_paiement);
    On_change_date_limite_paiement.call($('#id_modifier_date_limite_paiement').get(0));
});

// préfixe
function On_change_prefixe() {
    $('#div_id_prefixe').hide();
    if ($(this).prop("checked")) {
        $('#div_id_prefixe').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_prefixe').change(On_change_prefixe);
    On_change_prefixe.call($('#id_modifier_prefixe').get(0));
});

// Lot
function On_change_lot() {
    $('#div_id_lot').hide();
    if ($(this).prop("checked")) {
        $('#div_id_lot').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_lot').change(On_change_lot);
    On_change_lot.call($('#id_modifier_lot').get(0));
});

// Régie
function On_change_regie() {
    $('#div_id_regie').hide();
    if ($(this).prop("checked")) {
        $('#div_id_regie').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_regie').change(On_change_regie);
    On_change_regie.call($('#id_modifier_regie').get(0));
});

</script>
"""
