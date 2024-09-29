# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Div, ButtonHolder, Fieldset
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import ModeReglement
from core.utils import utils_preferences, utils_images
from core.widgets import Crop_image


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = ModeReglement
        fields = "__all__"
        widgets = {
            'image': Crop_image(attrs={"largeur_min": 132, "hauteur_min": 72, "ratio": "132/72"}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modes_reglements_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modes_reglements_liste' %}"),
            Field("cropper_data"),
            Fieldset('Généralités',
                Field('label'),
                Field('type_comptable'),
                Field('code_compta'),
                Field('code_journal'),
            ),
            Fieldset("Image",
                Field('image'),
            ),
            Fieldset('Numéro de pièce',
                Field('numero_piece'),
                Field('nbre_chiffres'),
            ),
            Fieldset('Frais de gestion',
                Field('frais_gestion'),
                PrependedText('frais_montant', utils_preferences.Get_symbole_monnaie()),
                PrependedText('frais_pourcentage', '%'),
                Field('frais_arrondi'),
                Field('frais_label'),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def save(self):
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get('cropper_data')
        # Recadrage de l'image
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.image)
        return form


EXTRA_SCRIPT = """
<script>

// Numéro de pièce
function On_change_numero_piece() {
    $('#div_id_nbre_chiffres').hide();

    if($(this).val() == 'NUM') {
        $('#div_id_nbre_chiffres').show();
    }
}
$(document).ready(function() {
    $('#id_numero_piece').change(On_change_numero_piece);
    On_change_numero_piece.call($('#id_numero_piece').get(0));
});

// Frais de gestion
function On_change_frais_gestion() {
    $('#div_id_frais_montant').hide();
    $('#div_id_frais_pourcentage').hide();
    $('#div_id_frais_arrondi').hide();
    $('#div_id_frais_label').hide();

    if($(this).val() == 'LIBRE') {
        $('#div_id_frais_label').show();
    }
    if($(this).val() == 'FIXE') {
        $('#div_id_frais_label').show();
        $('#div_id_frais_montant').show();
    }
    if($(this).val() == 'PRORATA') {
        $('#div_id_frais_label').show();
        $('#div_id_frais_pourcentage').show();
        $('#div_id_frais_arrondi').show();
    }
}
$(document).ready(function() {
    $('#id_frais_gestion').change(On_change_frais_gestion);
    On_change_frais_gestion.call($('#id_frais_gestion').get(0));
});

</script>
"""