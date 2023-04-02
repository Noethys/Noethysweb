# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Collaborateur
from core.widgets import DatePickerWidget
from core.widgets import Crop_image
from core.utils import utils_images


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    # Naissance
    date_naiss = forms.DateField(label="Date", required=False, widget=DatePickerWidget())

    class Meta:
        model = Collaborateur
        fields = ["civilite", "nom", "nom_jfille", "prenom", "date_naiss", "memo", "photo"]
        widgets = {
            'memo': forms.Textarea(attrs={'rows': 3}),
            'photo': Crop_image(attrs={"largeur_min": 200, "hauteur_min": 200, "ratio": "1/1"}),
        }
        help_texts = {
            "civilite": "Sélectionnez une civilité dans la liste déroulante.",
            "nom": "Saisissez le nom de famille en majuscules.",
            "prenom": "Saisissez le prénom en minuscules avec la première lettre majuscule.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'collaborateur_identite_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="collaborateur_identite_modifier", modifier_args="idcollaborateur=idcollaborateur", modifier=True, enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'collaborateur_identite' idcollaborateur=idcollaborateur %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Field("cropper_data"),
            Fieldset("Etat-civil",
                Field("civilite"),
                Field("nom"),
                Field("nom_jfille"),
                Field("prenom"),
            ),
            Fieldset("Divers",
                Field("memo"),
            ),
            Fieldset("Photo",
                Field("photo"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        return self.cleaned_data

    def save(self):
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get('cropper_data')
        # Recadrage de l'image
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.photo)
        return form


EXTRA_SCRIPT = """
<script>

// civilite
function On_change_civilite() {
    $('#div_id_nom_jfille').hide();
    if($(this).val() == "MME") {
        $('#div_id_nom_jfille').show();
    };
}
$(document).ready(function() {
    $('#id_civilite').change(On_change_civilite);
    On_change_civilite.call($('#id_civilite').get(0));
});

</script>
"""
