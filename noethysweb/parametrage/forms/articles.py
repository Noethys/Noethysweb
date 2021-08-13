# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Hidden
from crispy_forms.bootstrap import Field
from django_summernote.widgets import SummernoteInplaceWidget
from core.forms.base import FormulaireBase
from core.models import Article
from core.utils.utils_commandes import Commandes
from core.widgets import DateTimePickerWidget
from core.widgets import Crop_image
from core.utils import utils_images


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Article
        fields = "__all__"
        widgets = {
            "date_debut": DateTimePickerWidget(),
            "date_fin": DateTimePickerWidget(),
            "texte": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '220px'}}),
            "image": Crop_image(attrs={"largeur_min": 447, "hauteur_min": 251, "ratio": "16/9"}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'articles_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date de début de publication
        if not self.instance.pk:
            self.fields["date_debut"].initial = datetime.datetime.now()
            self.fields["auteur"].initial = self.request.user

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'articles_liste' %}"),
            Field("cropper_data"),
            Field("auteur", type="hidden"),
            Fieldset("Généralités",
                Field("titre"),
                Field("texte"),
                Field("image"),
            ),
            Fieldset("Options",
                Field("statut"),
                Field("date_debut"),
                Field("date_fin"),
                Field("couleur_fond"),
            ),
            Fieldset("Document joint",
                Field("document"),
                Field("document_titre"),
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
