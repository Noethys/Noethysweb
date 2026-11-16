# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os, uuid
from django import forms
from django.conf import settings
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase


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


def Analyser_photo(fichier=None, uuid_lot=None):
    """ Détecte les visages d'une photo et enregistre chaque portrait dans media/temp/<uuid_lot> """
    import cv2
    import numpy as np
    from PIL import Image

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

    # Charge l'image
    fichier.seek(0)
    image = np.asarray(bytearray(fichier.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Image illisible")
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
        img.save(os.path.join(rep_destination, "%s.jpg" % uuid.uuid4()))

    return len(rects)
