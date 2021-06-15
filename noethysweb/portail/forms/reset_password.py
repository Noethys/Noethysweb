# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from django.conf import settings
from django.forms import ValidationError
from django.core.validators import validate_email
from core.models import Utilisateur, AdresseMail
from django.core import mail as djangomail
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode



class MySetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super(MySetPasswordForm, self).__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs['class'] = "form-control"
        self.fields['new_password1'].widget.attrs['title'] = "Saisissez un nouveau mot de passe"
        self.fields['new_password1'].widget.attrs['placeholder'] = "Saisissez un nouveau mot de passe"
        self.fields['new_password2'].widget.attrs['class'] = "form-control"
        self.fields['new_password2'].widget.attrs['title'] = "Saisissez le nouveau mot de passe une nouvelle fois"
        self.fields['new_password2'].widget.attrs['placeholder'] = "Saisissez le nouveau mot de passe une nouvelle fois"



class MyPasswordResetForm(PasswordResetForm):
    identifiant = forms.CharField(label="Identifiant", max_length=20)
    email = forms.CharField(label="Email", max_length=254, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    if hasattr(settings, 'RECAPTCHA_PUBLIC_KEY'):
        captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox(attrs={'data-theme': 'light', 'data-size': 'normal'}))

    def __init__(self, *args, **kwargs):
        super(MyPasswordResetForm, self).__init__(*args, **kwargs)
        self.fields['identifiant'].widget.attrs['class'] = "form-control"
        self.fields['identifiant'].widget.attrs['title'] = "Saisissez l'identifiant qui vous a été communiqué par l'organisme. Si vous avez oublié cet identifiant, contactez l'organisme."
        self.fields['identifiant'].widget.attrs['placeholder'] = "Saisissez votre identifiant"
        self.fields['email'].widget.attrs['class'] = "form-control"
        self.fields['email'].widget.attrs['title'] = "Saisissez votre adresse Email"
        self.fields['email'].widget.attrs['placeholder'] = "Saisissez votre adresse Email"

    def clean(self):
        identifiant = self.cleaned_data['identifiant']
        email = self.cleaned_data['email']

        # Vérifie la cohérence de l'adresse mail
        try:
            validate_email(email)
        except:
            raise ValidationError("L'adresse Email n'est pas valide")

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

        # Recherche l'utilisateur
        utilisateur = Utilisateur.objects.filter(email__iexact=email, username__iexact=identifiant, is_active=True, categorie="famille").first()
        if not utilisateur:
            return "Il n'existe pas de compte actif correspondant à cet identifiant et cette adresse Email."

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
        adresse_exp = AdresseMail.objects.filter(defaut=True).first()
        if not adresse_exp:
            return "L'envoi de l'email a échoué. Merci de signaler cet incident à l'organisme."

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

        # Création de la connexion
        connection = djangomail.get_connection(backend=backend, fail_silently=False, **backend_kwargs)
        try:
            connection.open()
        except Exception as err:
            return "Connexion impossible au serveur de messagerie : %s" % err

        # Création du message
        objet = loader.render_to_string(subject_template_name, context)
        objet = ''.join(objet.splitlines())
        body = loader.render_to_string(email_template_name, context)

        message = EmailMultiAlternatives(subject=objet, body=body, from_email=adresse_exp.adresse, to=[utilisateur.email], connection=connection)

        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            message.attach_alternative(html_email, 'text/html')

        # Envoie le mail
        try:
            resultat = message.send()
        except Exception as err:
            resultat = err

        connection.close()
        return resultat
