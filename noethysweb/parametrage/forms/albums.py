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
from upload_form.forms import UploadForm
from PIL import Image


class Formulaire_album(FormulaireBase, ModelForm):

    class Meta:
        model = Album
        fields = ["titre", "description", "structure", "auteur"]
        widgets = {
            "description": SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '200px'}}),
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


class Formulaire_importation(UploadForm):
    idalbum = forms.IntegerField(label="", widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.idalbum = kwargs.pop("idalbum")
        super().__init__(*args, **kwargs)
        self.accept = settings.MY_UPLOAD_FORM_ACCEPT
        self.max_image_size = settings.MY_UPLOAD_FORM_MAX_IMAGE_SIZE
        self.fields["idalbum"].initial = self.idalbum

    def form_valid(self, request):
        fichiers = self.files.getlist('files')
        for fichier in fichiers:
            photo = Photo.objects.create(album_id=self.idalbum, fichier=fichier)
            try:
                date_creation = Image.open(settings.BASE_DIR + photo.fichier.url)._getexif()[36867]
            except:
                date_creation = None
            if date_creation:
                photo.date_creation = datetime.datetime.strptime(date_creation, "%Y:%m:%d %H:%M:%S")
                photo.save()
        return self.get_success_url(request)

    def get_success_url(self, request=None):
        return reverse_lazy("albums_consulter", kwargs={"pk": self.idalbum})

    def get_action(self, request=None):
        return reverse_lazy("ajax_importer_photos_album")
