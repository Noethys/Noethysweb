# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ValidationError
from django.utils.translation import gettext as _
from core.utils.utils_captcha import CaptchaField, CustomCaptchaTextInput_bs5


class FormLoginFamille(AuthenticationForm):
    captcha = CaptchaField(widget=CustomCaptchaTextInput_bs5)

    def __init__(self, *args, **kwargs):
        super(FormLoginFamille, self).__init__(*args, **kwargs)

        username_attrs = {
            'class': 'form-control',
            'placeholder': _("Identifiant"),
            'required': True,
            'aria-required': 'true',
            'autocomplete': 'username',
        }
        if self.errors.get('username'):
            username_attrs['class'] += ' is-invalid'
            username_attrs['aria-describedby'] = 'error-username'
        self.fields['username'].widget.attrs.update(username_attrs)

        password_attrs = {
            'class': 'form-control',
            'placeholder': _("Mot de passe"),
            'required': True,
            'aria-required': 'true',
            'autocomplete': 'current-password',
        }
        if self.errors.get('password'):
            password_attrs['class'] += ' is-invalid'
            password_attrs['aria-describedby'] = 'error-password'
        self.fields['password'].widget.attrs.update(password_attrs)

        captcha_attrs = {
            'class': 'form-control',
            'placeholder': _("Recopiez le code"),
            'required': True,
            'aria-required': 'true',
        }
        if self.errors.get('captcha'):
            captcha_attrs['class'] += ' is-invalid'
            captcha_attrs['aria-describedby'] = 'error-captcha'
        self.fields['captcha'].widget.attrs.update(captcha_attrs)

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(_("Ce compte a été désactivé"), code='inactive')
        if user.categorie != "famille":
            raise ValidationError(_("Accès non autorisé"), code='acces_interdit')
        if user.date_expiration_mdp and user.date_expiration_mdp < datetime.datetime.now():
            raise ValidationError(_("Ce mot de passe a expiré"), code='mdp_expire')
