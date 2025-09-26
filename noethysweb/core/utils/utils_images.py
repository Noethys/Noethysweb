# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from PIL import Image
try:
    from packaging.version import parse as parse_version
except:
    from pkg_resources import parse_version


def Recadrer_image_form(cropper_data=None, image=None):
    """ Enregistre l'image d'un form après cropper """
    # Adaptation pour PIL > 10.0.0
    if parse_version(Image.__version__) >= parse_version("10.0.0"):
        Image.ANTIALIAS = Image.LANCZOS

    cropper_data = json.loads(cropper_data)
    img = Image.open(image)
    img = img.rotate(-cropper_data["rotate"], expand=True)
    img = img.crop((cropper_data["x"], cropper_data["y"], cropper_data["width"] + cropper_data["x"], cropper_data["height"] + cropper_data["y"]))
    img = img.resize((cropper_data["largeur"], int(cropper_data["largeur"] / cropper_data["ratio"])), Image.ANTIALIAS)
    img.save(image.path)

