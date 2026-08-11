# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.
#
#  Prérequis pour le bouton audio du captcha :
#  1. Installer le moteur de synthèse vocale utilisé par django-simple-captcha :
#        pip install django-simple-captcha[audio]
#     ou, selon la config choisie dans settings.py :
#        pip install gTTS          # moteur Google TTS (recommandé, nécessite internet)
#        pip install pyttsx3       # moteur local, ne nécessite pas internet
#
#  2. Ajouter dans settings.py :
#        CAPTCHA_FLITE_PATH = "/usr/bin/flite"   # si flite est utilisé (Linux)
#     ou :
#        CAPTCHA_NOISE_FUNCTIONS = ()
#        CAPTCHA_CHALLENGE_FUNCT = 'core.utils.utils_captcha.random_digit_challenge'
#
#  3. S'assurer que CAPTCHA_AUDIO_FACTORY est défini dans settings.py
#     pour que {{ audio }} soit non vide dans le template :
#        CAPTCHA_AUDIO_FACTORY = 'captcha.audio.NoiseAudioFactory'  # valeur par défaut

import random
from captcha.fields import CaptchaField, CaptchaTextInput


class CustomCaptchaTextInput_bs4(CaptchaTextInput):
    template_name = "core/captcha.html"


class CustomCaptchaTextInput_bs5(CaptchaTextInput):
    template_name = "portail/captcha.html"


def random_digit_challenge():
    texte = "".join([str(random.choice("2345689")) for i in range(3)])
    return texte, texte