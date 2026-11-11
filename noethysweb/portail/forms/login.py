# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ValidationError
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from axes.models import AccessAttempt
from django.utils.translation import gettext as _
from core.utils.utils_captcha import CaptchaField, CustomCaptchaTextInput_bs5


def Is_compte_bloque(identifiant=None):
    """ Renvoie True si le compte a dépassé le nombre d'échecs de connexion autorisés sur la période de blocage, toutes adresses IP confondues """
    limite = getattr(settings, "PORTAIL_LIMITE_ECHECS_COMPTE", 20)
    if not identifiant or not limite:
        return False
    resultat = AccessAttempt.objects.filter(username__iexact=identifiant, attempt_time__gte=timezone.now() - datetime.timedelta(hours=getattr(settings, "PORTAIL_DUREE_BLOCAGE_COMPTE", 24))).aggregate(total=Sum("failures_since_start"))
    return (resultat["total"] or 0) >= limite


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

    def clean(self):
        # Le mot de passe n'est pas vérifié si le code de sécurité est faux (sinon le captcha pourrait être contourné)
        if "captcha" in self.errors:
            return self.cleaned_data
        # Blocage temporaire du compte si trop d'échecs récents, quelle que soit l'adresse IP
        if Is_compte_bloque(self.cleaned_data.get("username")):
            raise ValidationError(_("Trop de tentatives de connexion sur ce compte. Veuillez réessayer dans %d heures ou utiliser la fonction 'Mot de passe oublié'.") % getattr(settings, "PORTAIL_DUREE_BLOCAGE_COMPTE", 24), code="compte_bloque")
        return super(FormLoginFamille, self).clean()

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(_("Ce compte a été désactivé"), code='inactive')
        if user.categorie != "famille":
            raise ValidationError(_("Accès non autorisé"), code='acces_interdit')
        if user.date_expiration_mdp and user.date_expiration_mdp < datetime.datetime.now():
            raise ValidationError(_("Ce mot de passe a expiré"), code='mdp_expire')
