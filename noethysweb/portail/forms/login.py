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
        if ((user.categorie not in ["famille", "individu"])  # Vérification de la catégorie : Si l'utilisateur n'est ni "famille" ni "individu", l'accès est interdit.
                or (compte_famille != "True" and user.categorie == "famille")   #Compte famille non activé pour une famille: Si compte_famille n'est pas "True" et que la catégorie est "famille", l'accès est interdit.
                or ( compte_individu == "True" and user.categorie == "famille")): #Compte individu activé pour une famille: Si compte_individu est "True" alors que l'utilisateur est de catégorie "famille", l'accès est interdit.
            raise ValidationError(_("Accès non autorisé"), code='acces_interdit')
        if user.date_expiration_mdp and user.date_expiration_mdp < datetime.datetime.now():
            raise ValidationError(_("Ce mot de passe a expiré"), code='mdp_expire')