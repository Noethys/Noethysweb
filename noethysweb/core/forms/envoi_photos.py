# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from django.conf import settings
from django.core.validators import FileExtensionValidator


# Formats photo acceptés (extension du fichier et format réel détecté par Pillow)
EXTENSIONS_AUTORISEES = ["jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff"]
FORMATS_AUTORISES = {"JPEG", "MPO", "PNG", "GIF", "WEBP", "BMP", "TIFF"}


def Get_taille_max_mo():
    return getattr(settings, "PHOTOS_TAILLE_MAX_MO", 10)


def Get_dimension_max():
    return getattr(settings, "PHOTOS_DIMENSION_MAX", 2000)


def Get_pixels_max():
    return getattr(settings, "PHOTOS_PIXELS_MAX", 40000000)


def Get_contexte_zone_envoi(url="", url_fin="", libelle_bouton="Envoyer", extra=None):
    """ Contexte à transmettre au gabarit core/widgets/zone_envoi_photos.html """
    return {
        "url": url,
        "url_fin": url_fin,
        "libelle_bouton": libelle_bouton,
        "extra_json": json.dumps(extra or {}),
        "taille_max": Get_taille_max_mo(),
        "dimension_max": Get_dimension_max(),
    }


class Formulaire_envoi_photo(forms.Form):
    """ Réception d'une photo envoyée par la zone d'envoi """
    fichier = forms.ImageField(validators=[FileExtensionValidator(EXTENSIONS_AUTORISEES, message="Format non accepté")])
    date_prise = forms.CharField(required=False, max_length=19)

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]
        if fichier.size > Get_taille_max_mo() * 1024 * 1024:
            raise forms.ValidationError("Fichier trop volumineux (%d Mo maximum)" % Get_taille_max_mo())
        if getattr(fichier.image, "format", None) not in FORMATS_AUTORISES:
            raise forms.ValidationError("Format non accepté")
        # Protection contre les images piégées (petit fichier, dimensions énormes une fois décodé)
        largeur, hauteur = fichier.image.size
        if largeur * hauteur > Get_pixels_max():
            raise forms.ValidationError("Image trop grande (%d x %d pixels)" % (largeur, hauteur))
        return fichier

    def clean_date_prise(self):
        valeur = self.cleaned_data.get("date_prise")
        if not valeur:
            return None
        try:
            return datetime.datetime.strptime(valeur, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            return None

    def Get_erreur(self):
        for erreurs in self.errors.values():
            return erreurs[0]
        return "Fichier invalide"
