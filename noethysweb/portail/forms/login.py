# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.
import logging
logger = logging.getLogger(__name__)
import datetime
from django.contrib.auth.forms import AuthenticationForm
from django.forms import ValidationError
from django.utils.translation import gettext as _
from core.utils.utils_captcha import CaptchaField, CustomCaptchaTextInput
from core.models import PortailParametre


class FormLogin(AuthenticationForm):
    captcha = CaptchaField(widget=CustomCaptchaTextInput)

    def __init__(self, *args, **kwargs):
        super(FormLogin, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = "form-control"
        self.fields['username'].widget.attrs['placeholder'] = _("Identifiant")
        self.fields['password'].widget.attrs['class'] = "form-control"
        self.fields['password'].widget.attrs['placeholder'] = _("Mot de passe")
        self.fields['captcha'].widget.attrs['class'] = "form-control"
        self.fields['captcha'].widget.attrs['placeholder'] = _("Recopiez le code de sécurité ci-contre")

    def confirm_login_allowed(self, user):
        compte_famille = PortailParametre.objects.filter(code="compte_famille").first()
        compte_individu = PortailParametre.objects.filter(code="compte_individu").first()

        if not user.is_active:
            raise ValidationError(_("Ce compte a été désactivé"), code='inactive')

        # Vérification de la catégorie
        if user.categorie not in ["famille", "individu"]:
            raise ValidationError(_("Accès non autorisé"), code='acces_interdit')

        # Pour les utilisateurs de catégorie 'famille'
        if user.categorie == "famille":
            # Vérifie que le paramètre compte_famille existe et est activé
            if not compte_famille or compte_famille.valeur != "True":
                raise ValidationError(_("Accès non autorisé"), code='acces_interdit')

        # Pour les utilisateurs de catégorie 'individu'
        if user.categorie == "individu":
            # Vérifie que le paramètre compte_individu existe et est activé
            if not compte_individu or compte_individu.valeur != "True":
                raise ValidationError(_("Accès non autorisé"), code='acces_interdit')

        if user.date_expiration_mdp and user.date_expiration_mdp < datetime.datetime.now():
            raise ValidationError(_("Ce mot de passe a expiré"), code='mdp_expire')
