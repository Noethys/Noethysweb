# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ValidationError
from core.utils.utils_captcha import CaptchaField, CustomCaptchaTextInput


class FormLoginFamille(AuthenticationForm):
    captcha = CaptchaField(widget=CustomCaptchaTextInput)

    def __init__(self, *args, **kwargs):
        super(FormLoginFamille, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = "form-control"
        self.fields['username'].widget.attrs['placeholder'] = "Identifiant"
        self.fields['password'].widget.attrs['class'] = "form-control"
        self.fields['password'].widget.attrs['placeholder'] = "Mot de passe"
        self.fields['captcha'].widget.attrs['class'] = "form-control"
        self.fields['captcha'].widget.attrs['placeholder'] = "Recopiez le code de sécurité ci-contre"

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError("Ce compte a été désactivé", code='inactive')
        if user.categorie != "famille":
            raise ValidationError("Accès non autorisé", code='acces_interdit')
        if user.date_expiration_mdp and user.date_expiration_mdp < datetime.datetime.now():
            raise ValidationError("Ce mot de passe a expiré.", code='mdp_expire')
