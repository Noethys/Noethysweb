# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, uuid
from django import forms
from django.urls import reverse_lazy
from django.conf import settings
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from upload_form.forms import UploadForm


class Formulaire(FormulaireBase, forms.Form):
    data = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_importation_photos'
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False
        self.helper.use_custom_control = False

        # Affichage
        self.helper.layout = Layout(
            Field('data'),
        )


class Formulaire_importation(UploadForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accept = settings.MY_UPLOAD_FORM_ACCEPT
        self.max_image_size = settings.MY_UPLOAD_FORM_MAX_IMAGE_SIZE

    def form_valid(self, request):
        fichiers = self.files.getlist('files')
        uuid_lot = self.Analyse_photos(fichiers=fichiers)
        return uuid_lot

    def get_action(self, request=None):
        return reverse_lazy("ajax_importer_photos_individus")

    def Analyse_photos(self, fichiers=[]):
        import cv2
        import numpy as np
        from PIL import Image

        # Création du nom du répertoire
        uuid_lot = uuid.uuid4()

        # Recherche l'algorithme de détection
        face_detector = None
        try:
            face_detector = "{base_path}/data/haarcascade_frontalface_default.xml".format(base_path=cv2.__path__[0])
        except:
            pass
        if not face_detector:
            face_detector = "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml"

        # Charge l'algorithme de détection
        detector = cv2.CascadeClassifier(face_detector)

        for fichier in fichiers:

            # Charge l'image
            image = np.asarray(bytearray(fichier.file.read()), dtype="uint8")
            image = cv2.imdecode(image, cv2.IMREAD_COLOR)
            image_nb = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            image_couleur = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_pil = Image.fromarray(image_couleur)

            # Création du répertoire temp
            rep_destination = os.path.join(settings.MEDIA_ROOT, "temp", str(uuid_lot))
            if not os.path.exists(rep_destination):
                os.makedirs(rep_destination)

            # Analyse l'image
            rects = detector.detectMultiScale(image_nb, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
            for (x, y, w, h) in rects:
                # Ajout d'une marge
                marge = w * 10//100
                x, y, w, h = x-marge, y-marge, w+marge*2, h+marge*2

                # Découpe chaque portrait
                img = image_pil.crop((x, y, x + w, y + h))
                nom_fichier = os.path.join(rep_destination, "%s.jpg" % uuid.uuid4())
                img.save(os.path.join(settings.MEDIA_ROOT, nom_fichier))

                # Tracé du cadre rouge sur la photo originale
                cv2.rectangle(image_couleur, (x, y), (x + w, y + h), (255, 0, 0), 2)

        return uuid_lot
