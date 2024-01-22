# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Row, Column, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import TypePiece
from core.widgets import DatePickerWidget
from django.utils.dateparse import parse_date


class Formulaire(FormulaireBase, ModelForm):
    # Modification du label de la checkbox
    valide_rattachement = forms.BooleanField(label="La pièce est également valable pour les familles rattachées à l'individu.", required=False)

    # Champs libres pour la durée de validité
    choix_validite = [("ILLIMITEE", "Validité illimitée"), ("DUREE", "Une durée"), ("DATE", "Une date"), ]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='ILLIMITEE', required=True)
    validite_jours = forms.IntegerField(label="Jours", required=False)
    validite_mois = forms.IntegerField(label="Mois", required=False)
    validite_annees = forms.IntegerField(label="Années", required=False)
    validite_date = forms.DateField(label="Date de fin de validité*", required=False, widget=DatePickerWidget())

    class Meta:
        model = TypePiece
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'types_pieces_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Validité
        self.fields["validite_jours"].widget.attrs.update({"min": 0})
        self.fields["validite_mois"].widget.attrs.update({"min": 0})
        self.fields["validite_annees"].widget.attrs.update({"min": 0})

        # Importe la durée de validité dans les champs libres
        if self.instance.duree_validite == None:
            # Durée illimitée
            self.fields['validite_type'].initial = "ILLIMITEE"
        elif self.instance.duree_validite.startswith("j"):
            # Si validité par durée
            self.fields['validite_type'].initial = "DUREE"
            jours, mois, annees = self.instance.duree_validite.split("-")
            self.fields['validite_jours'].initial = int(jours[1:])
            self.fields['validite_mois'].initial = int(mois[1:])
            self.fields['validite_annees'].initial = int(annees[1:])
        elif self.instance.duree_validite.startswith("d"):
            # Si validité par date
            self.fields['validite_type'].initial = "DATE"
            self.fields['validite_date'].initial = parse_date(self.instance.duree_validite[1:])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_pieces_liste' %}"),
            Fieldset('Généralités',
                Field('nom'),
                Field('structure'),
                Field('public'),
                Field('valide_rattachement'),
            ),
            Fieldset('Durée de validité',
                Field('validite_type'),
                Div(
                    Field('validite_annees'),
                    Field('validite_mois'),
                    Field('validite_jours'),
                    id='bloc_duree'
                ),
                Field('validite_date'),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        """ Convertit les champs de validité en un seul champ duree_validite """
        # Durée illimitée
        if self.cleaned_data["validite_type"] == "ILLIMITEE":
            self.cleaned_data["duree_validite"] = None

        # Validité par durée
        if self.cleaned_data["validite_type"] == "DUREE":
            jours = int(self.cleaned_data["validite_jours"] or 0)
            mois = int(self.cleaned_data["validite_mois"] or 0)
            annees = int(self.cleaned_data["validite_annees"] or 0)
            if jours == 0 and mois == 0 and annees == 0:
                self.add_error('validite_type', "Vous devez saisir une durée en jours et/ou mois et/ou années")
                return
            self.cleaned_data["duree_validite"] = "j%d-m%d-a%d" % (jours, mois, annees)

        # Validité par date
        if self.cleaned_data["validite_type"] == "DATE":
            if self.cleaned_data["validite_date"] == None:
                self.add_error('validite_date', "Vous devez sélectionner une date")
                return
            self.cleaned_data["duree_validite"] = "d%s" % self.cleaned_data["validite_date"]

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// public
function On_change_public() {
    $('#div_id_valide_rattachement').hide();

    if($(this).val() == 'individu') {
        $('#div_id_valide_rattachement').show();
    }
}
$(document).ready(function() {
    $('#id_public').change(On_change_public);
    On_change_public.call($('#id_public').get(0));
});

// validite_type
function On_change_validite_type() {
    $('#bloc_duree').hide();
    $('#div_id_validite_date').hide();

    if($(this).val() == 'DUREE') {
        $('#bloc_duree').show();
    }
    if($(this).val() == 'DATE') {
        $('#div_id_validite_date').show();
    }
}
$(document).ready(function() {
    $('#id_validite_type').change(On_change_validite_type);
    On_change_validite_type.call($('#id_validite_type').get(0));
});

</script>
"""