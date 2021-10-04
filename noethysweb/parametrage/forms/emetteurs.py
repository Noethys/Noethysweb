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
from core.models import Emetteur
from core.widgets import Crop_image
from core.utils import utils_images


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Emetteur
        fields = "__all__"
        widgets = {
            'image': Crop_image(attrs={"largeur_min": 132, "hauteur_min": 72, "ratio": "132/72"}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'Emetteurs_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'emetteurs_liste' %}"),
            Field("cropper_data"),
            Fieldset('Généralités',
                Field('nom'),
                Field('mode'),
            ),
            Fieldset("Image",
                Field('image'),
            ),
        )

    def save(self):
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get('cropper_data')
        # Recadrage de l'image
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.image)
        return form
