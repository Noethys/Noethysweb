# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder, Div
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Information, Individu
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    # Durée de validité
    choix_validite = [("ILLIMITEE", "Durée illimitée"), ("LIMITEE", "Durée limitée")]
    validite_type = forms.TypedChoiceField(label="Validité", choices=choix_validite, initial='ILLIMITEE', required=False)
    date_debut = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget())

    # Traitement
    date_debut_traitement = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget())
    date_fin_traitement = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget())

    # Eviction
    date_debut_eviction = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget())
    date_fin_eviction = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget())

    class Meta:
        model = Information
        fields = "__all__"
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'description_traitement': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_informations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "individu") == False:
            individu = Individu.objects.get(pk=idindividu)
        else:
            individu = self.instance.individu

        # Importe la durée de validité
        if self.instance.date_debut or self.instance.date_fin :
            self.fields['validite_type'].initial = "LIMITEE"
        else:
            self.fields['validite_type'].initial = "ILLIMITEE"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('page', value="info_medicale"),
            Hidden('individu', value=individu.idindividu),
            Fieldset("Généralités",
                Field("categorie"),
                Field("intitule"),
                Field("description"),
                Field("validite_type"),
                Div(
                    Field("date_debut"),
                    Field("date_fin"),
                    id="periode_validite",
                ),
            ),
            Fieldset("Document numérisé",
                Field("document"),
            ),
            Fieldset("Traitement médical",
                Field("traitement_medical"),
                Div(
                    Field("description_traitement"),
                    Field("date_debut_traitement"),
                    Field("date_fin_traitement"),
                    id="div_traitement",
                ),
            ),
            Fieldset("Eviction de l'activité",
                Field("eviction"),
                Div(
                    Field("date_debut_eviction"),
                    Field("date_fin_eviction"),
                    id="div_eviction",
                ),
            ),
            Fieldset("Diffusion de l'information",
                Field("diffusion_listing_enfants"),
                Field("diffusion_listing_conso"),
                Field("diffusion_listing_repas"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Validité
function On_change_validite() {
    $('#periode_validite').hide();
    if($(this).val() == 'LIMITEE') {
        $('#periode_validite').show();
    }
}
$(document).ready(function() {
    $('#id_validite_type').change(On_change_validite);
    On_change_validite.call($('#id_validite_type').get(0));
});


// Traitement
function On_change_traitement() {
    $('#div_traitement').hide();
    if ($(this).prop("checked")) {
        $('#div_traitement').show();
    }
}
$(document).ready(function() {
    $('#id_traitement_medical').on('change', On_change_traitement);
    On_change_traitement.call($('#id_traitement_medical').get(0));
});

// Eviction
function On_change_eviction() {
    $('#div_eviction').hide();
    if ($(this).prop("checked")) {
        $('#div_eviction').show();
    }
}
$(document).ready(function() {
    $('#id_eviction').on('change', On_change_eviction);
    On_change_eviction.call($('#id_eviction').get(0));
});



</script>
"""