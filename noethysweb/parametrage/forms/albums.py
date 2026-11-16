# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.conf import settings
from django.forms import ModelForm
from django.urls import reverse_lazy
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Album, Photo
from core.widgets import DateTimePickerWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from django_summernote.widgets import SummernoteInplaceWidget
from PIL import Image


class Formulaire_album(FormulaireBase, ModelForm):

    class Meta:
        model = Album
        fields = ["titre", "description", "structure", "auteur"]
        widgets = {
            "description": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '200px'}}),
        }
        help_texts = {
            "structure": "Sélectionnez la structure associée à ce album. Laissez 'Toutes les structures' pour que ce album soit disponible dans toutes les structures.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire_album, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'albums_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'albums_liste' %}", ajouter=False),
            Field("auteur", type="hidden"),
            Fieldset("Généralités",
                Field("titre"),
                Field("description"),
            ),
            Fieldset("Structure associée",
                Field("structure"),
            ),
        )


class Formulaire_photo(FormulaireBase, ModelForm):

    class Meta:
        model = Photo
        fields = ["titre", "date_creation", "fichier"]
        widgets = {
            "date_creation": DateTimePickerWidget(),
        }
        help_texts = {
            "fichier": "Sélectionnez le fichier image de la photo (format JPG ou PNG).",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire_photo, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'photo_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'albums_consulter' pk=photo.album_id %}", ajouter=False),
            Field("titre"),
            Field("date_creation"),
            Field("fichier"),
        )
