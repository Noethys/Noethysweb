# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.utils.translation import gettext as _
from django.forms import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import get_password_validators
from django.conf import settings
from core.utils.utils_captcha import CaptchaField, CustomCaptchaTextInput_bs5
from portail.utils import utils_secquest


class MySetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(MySetPasswordForm, self).__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['class'] = "form-control"
        self.fields['new_password1'].widget.attrs['title'] = _("Saisissez un nouveau mot de passe")
        self.fields['new_password1'].widget.attrs['placeholder'] = _("Saisissez un nouveau mot de passe")
        self.fields['new_password2'].widget.attrs['class'] = "form-control"
        self.fields['new_password2'].widget.attrs['title'] = _("Saisissez le nouveau mot de passe une nouvelle fois")
        self.fields['new_password2'].widget.attrs['placeholder'] = _("Saisissez le nouveau mot de passe une nouvelle fois")

        # Question
        if kwargs["user"].famille.internet_secquest:
            self.fields["secquest"] = utils_secquest.Generation_field_secquest(famille=kwargs["user"].famille)

        # Affichage des exigences de mot de passe dans le help_text
        exigences = ["<li>%s</li>" % v.get_help_text() for v in get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)]
        self.fields["new_password1"].help_text = "<ul style='padding-left: 16px;padding-bottom: 0px;margin-bottom: 0;'>%s</ul>" % "".join(exigences)


class MyPasswordResetForm(PasswordResetForm):
    identifiant = forms.CharField(label="Identifiant", max_length=20)
    email = forms.CharField(label="Email", max_length=254, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    captcha = CaptchaField(widget=CustomCaptchaTextInput_bs5)

    def __init__(self, *args, **kwargs):
        super(MyPasswordResetForm, self).__init__(*args, **kwargs)
        self.fields['identifiant'].widget.attrs['class'] = "form-control"
        self.fields['identifiant'].widget.attrs['title'] = _("Saisissez l'identifiant qui vous a été communiqué par l'organisme. Si vous avez oublié cet identifiant, contactez l'organisme.")
        self.fields['identifiant'].widget.attrs['placeholder'] = _("Saisissez votre identifiant")
        self.fields['email'].widget.attrs['class'] = "form-control"
        self.fields['email'].widget.attrs['title'] = _("Saisissez votre adresse Email")
        self.fields['email'].widget.attrs['placeholder'] = _("Saisissez votre adresse Email")
        self.fields['captcha'].widget.attrs['class'] = "form-control"
        self.fields['captcha'].widget.attrs['placeholder'] = _("Recopiez le code de sécurité")

    def clean(self):
        # Vérifie la cohérence de l'adresse mail
        try:
            validate_email(self.cleaned_data["email"])
        except:
            raise ValidationError(_("L'adresse Email n'est pas valide"))

        return self.cleaned_data
