# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.utils import utils_images
from core.models import CategorieEvenement, Activite
from core.widgets import Crop_image


class Formulaire(FormulaireBase, ModelForm):
    # Image
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = CategorieEvenement
        fields = "__all__"
        widgets = {
            "image": Crop_image(attrs={"largeur_min": 400, "hauteur_min": 100, "ratio": "400/100"}),
        }
        help_texts = {
            "image": "Vous pouvez sélectionner une image à appliquer sur l'arrière-plan de la case des événements liés dans la grille des consommations. L'image sera convertie en niveaux de gris à l'affichage.",
        }

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_evenements_categories_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "activite") == False:
            activite = Activite.objects.get(pk=idactivite)
        else:
            activite = self.instance.activite

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden("activite", value=activite.idactivite),
            Field("cropper_data"),
            Fieldset("Généralités",
                Field("nom"),
            ),
            Fieldset("Image d'arrière-plan",
                Field("image"),
            ),
            Fieldset("Options",
                Field("limitations"),
            ),
        )

    def save(self):
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get("cropper_data")
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.image)
        return form
