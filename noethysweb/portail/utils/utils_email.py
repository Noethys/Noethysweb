# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.utils.translation import gettext as _
from django.core import mail as djangomail
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from core.models import AdresseMail, Organisateur
from core.utils import utils_portail


def Envoyer_email(utilisateur=None, domain_override=None,
        nom_template_sujet=None, nom_template_texte=None, nom_template_html=None,
        request=None, token=None, extra_email_context=None):
    """ Envoi d'un email avec un token """

    if not domain_override:
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
    else:
        site_name = domain = domain_override
    context = {
        "email": utilisateur,
        "domain": domain,
        "site_name": site_name,
        "uid": urlsafe_base64_encode(force_bytes(utilisateur.pk)) if utilisateur else None,
        "user": utilisateur,
        "token": token,
        "protocol": "https" if request.is_secure() else "http",
        "organisateur": Organisateur.objects.filter(pk=1).first(),
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

    # Backend MICROSOFT 365 (API Graph + OAuth2)
    if adresse_exp.moteur == "microsoft365":
        backend = 'outils.utils.backend_microsoft365.EmailBackend'
        backend_kwargs = {"tenant_id": adresse_exp.Get_parametre("tenant_id"), "client_id": adresse_exp.Get_parametre("client_id"), "client_secret": adresse_exp.motdepasse}

    # Création de la connexion
    connection = djangomail.get_connection(backend=backend, fail_silently=False, **backend_kwargs)
    try:
        connection.open()
    except Exception as err:
        logger.debug("Erreur : Connexion impossible au serveur de messagerie : %s." % err)
        return "Connexion impossible au serveur de messagerie : %s" % err

    # Création du message
    objet = loader.render_to_string(nom_template_sujet, context)
    objet = ''.join(objet.splitlines())

    text_content = loader.render_to_string(nom_template_texte, context)
    message = EmailMultiAlternatives(subject=objet, body=text_content, from_email=adresse_exp.adresse, to=[utilisateur.famille.mail], connection=connection)

    if nom_template_html is not None:
        html_content = loader.render_to_string(nom_template_html, context)
        message.attach_alternative(html_content, "text/html")

    # Envoie le mail
    try:
        resultat = message.send()
    except Exception as err:
        logger.debug("Erreur : Envoi du mail impossible : %s." % err)
        resultat = err

    if resultat == 1:
        logger.debug("Message envoyé.")
    if resultat == 0:
        logger.debug("Message non envoyé.")
        return _("L'envoi de l'email a échoué. Merci de signaler cet incident à l'organisateur.")

    connection.close()

    return resultat
