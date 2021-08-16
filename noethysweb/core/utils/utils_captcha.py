# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import random
from captcha.fields import CaptchaField, CaptchaTextInput


class CustomCaptchaTextInput(CaptchaTextInput):
    template_name = "core/captcha.html"


def random_digit_challenge():
    texte = "".join([str(random.choice("2345689")) for i in range(3)])
    return texte, texte
