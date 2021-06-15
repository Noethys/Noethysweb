# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from PIL import Image
import json


def Recadrer_image_form(cropper_data=None, image=None):
    """ Enregistre l'image d'un form après cropper """
    cropper_data = json.loads(cropper_data)
    img = Image.open(image)
    img = img.rotate(-cropper_data["rotate"], expand=True)
    img = img.crop((cropper_data["x"], cropper_data["y"], cropper_data["width"] + cropper_data["x"], cropper_data["height"] + cropper_data["y"]))
    img = img.resize((cropper_data["largeur"], int(cropper_data["largeur"] / cropper_data["ratio"])), Image.ANTIALIAS)
    img.save(image.path)

