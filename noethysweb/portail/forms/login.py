# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.forms import ValidationError


class FormLoginFamille(AuthenticationForm):
    if hasattr(settings, 'RECAPTCHA_PUBLIC_KEY'):
        captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox(attrs={'data-theme': 'light', 'data-size': 'normal'}))

    def __init__(self, *args, **kwargs):
        super(FormLoginFamille, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = "form-control"
        self.fields['username'].widget.attrs['placeholder'] = "Identifiant"
        self.fields['password'].widget.attrs['class'] = "form-control"
        self.fields['password'].widget.attrs['placeholder'] = "Mot de passe"

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError("Ce compte a été désactivé", code='inactive')
        if user.categorie != "famille":
            raise ValidationError("Accès non autorisé", code='acces_interdit')
