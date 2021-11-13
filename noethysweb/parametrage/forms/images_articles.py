# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import ImageArticle
from core.utils.utils_commandes import Commandes
from core.widgets import Crop_image
from core.utils import utils_images


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = ImageArticle
        fields = "__all__"
        widgets = {
            "image": Crop_image(attrs={"largeur_min": 447, "hauteur_min": 167, "ratio": "447/167"}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'images_articles_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'images_articles_liste' %}"),
            Field("cropper_data"),
            Fieldset("Généralités",
                Field("titre"),
                Field("image"),
            ),
            Fieldset("Structure associée",
                Field("structure"),
            ),
        )

    def save(self):
        """ Recadrage de l'image """
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get('cropper_data')
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.image)
        return form
