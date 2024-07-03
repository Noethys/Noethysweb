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
from django.core import mail as djangomail
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from core.models import Utilisateur, AdresseMail
from core.utils.utils_captcha import CaptchaField, CustomCaptchaTextInput
from core.utils import utils_portail
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


class MyPasswordResetForm(PasswordResetForm):
    identifiant = forms.CharField(label="Identifiant", max_length=20)
    email = forms.CharField(label="Email", max_length=254, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    captcha = CaptchaField(widget=CustomCaptchaTextInput)

    def __init__(self, *args, **kwargs):
        super(MyPasswordResetForm, self).__init__(*args, **kwargs)
        self.fields['identifiant'].widget.attrs['class'] = "form-control"
        self.fields['identifiant'].widget.attrs['title'] = _("Saisissez l'identifiant qui vous a été communiqué par l'organisme. Si vous avez oublié cet identifiant, contactez l'organisme.")
        self.fields['identifiant'].widget.attrs['placeholder'] = _("Saisissez votre identifiant")
        self.fields['email'].widget.attrs['class'] = "form-control"
        self.fields['email'].widget.attrs['title'] = _("Saisissez votre adresse Email")
        self.fields['email'].widget.attrs['placeholder'] = _("Saisissez votre adresse Email")
        self.fields['captcha'].widget.attrs['class'] = "form-control"
        self.fields['captcha'].widget.attrs['placeholder'] = _("Recopiez le code de sécurité ci-contre")

    def clean(self):
        identifiant = self.cleaned_data['identifiant']
        email = self.cleaned_data['email']

        # Vérifie la cohérence de l'adresse mail
        try:
            validate_email(email)
        except:
            raise ValidationError(_("L'adresse Email n'est pas valide"))

        return self.cleaned_data

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        identifiant = self.cleaned_data["identifiant"]
        email = self.cleaned_data["email"]
        logger.debug("Demande de reset du password : %s %s." % (identifiant, email))

        # Recherche l'utilisateur
        utilisateur = Utilisateur.objects.filter(username__iexact=identifiant, is_active=True, categorie="famille").first()
        if not utilisateur or not utilisateur.famille.mail or utilisateur.famille.mail != email:
            logger.debug("Erreur : Pas de compte actif existant.")
            return _("Il n'existe pas de compte actif correspondant à cet identifiant et cette adresse Email.")

        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override
        context = {
            'email': utilisateur,
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(utilisateur.pk)),
            'user': utilisateur,
            'token': token_generator.make_token(utilisateur),
            'protocol': 'https' if use_https else 'http',
            **(extra_email_context or {}),
        }

        # Importation de l'adresse d'expédition d'emails
        idadresse_exp = utils_portail.Get_parametre(code="connexion_adresse_exp")
        adresse_exp = None
        if idadresse_exp:
            adresse_exp = AdresseMail.objects.get(pk=idadresse_exp, actif=True)
        if not adresse_exp:
            logger.debug("Erreur : Pas d'adresse d'expédition paramétrée pour l'envoi du mail.")
            return _("L'envoi de l'email a échoué. Merci de signaler cet incident à l'organisateur.")

        # Backend CONSOLE (Par défaut)
        backend = 'django.core.mail.backends.console.EmailBackend'
        backend_kwargs = {}

        # Backend SMTP
        if adresse_exp.moteur == "smtp":
            backend = 'django.core.mail.backends.smtp.EmailBackend'
            backend_kwargs = {"host": adresse_exp.hote, "port": adresse_exp.port, "username": adresse_exp.utilisateur,
                              "password": adresse_exp.motdepasse, "use_tls": adresse_exp.use_tls}

        # Backend MAILJET
        if adresse_exp.moteur == "mailjet":
            backend = 'anymail.backends.mailjet.EmailBackend'
            backend_kwargs = {"api_key": adresse_exp.Get_parametre("api_key"), "secret_key": adresse_exp.Get_parametre("api_secret"), }

        # Backend BREVO
        if adresse_exp.moteur == "brevo":
            backend = 'anymail.backends.sendinblue.EmailBackend'
            backend_kwargs = {"api_key": adresse_exp.Get_parametre("api_key")}

        # Création de la connexion
        connection = djangomail.get_connection(backend=backend, fail_silently=False, **backend_kwargs)
        try:
            connection.open()
        except Exception as err:
            logger.debug("Erreur : Connexion impossible au serveur de messagerie : %s." % err)
            return "Connexion impossible au serveur de messagerie : %s" % err

        # Création du message
        objet = loader.render_to_string(subject_template_name, context)
        objet = ''.join(objet.splitlines())
        body = loader.render_to_string(email_template_name, context)

        message = EmailMultiAlternatives(subject=objet, body=body, from_email=adresse_exp.adresse, to=[utilisateur.famille.mail], connection=connection)

        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            message.attach_alternative(html_email, 'text/html')

        # Envoie le mail
        try:
            resultat = message.send()
        except Exception as err:
            logger.debug("Erreur : Envoi du mail de reset impossible : %s." % err)
            resultat = err

        if resultat == 1:
            logger.debug("Message de reset password envoyé.")
        if resultat == 0:
            logger.debug("Message de reset password non envoyé.")
            return _("L'envoi de l'email a échoué. Merci de signaler cet incident à l'organisateur.")

        connection.close()

        # Génération du secquest
        utils_secquest.Generation_secquest(famille=utilisateur.famille)

        return resultat
