# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.contrib.auth import views as auth_views
from django.contrib.auth.tokens import default_token_generator
from core.models import Utilisateur
from portail.forms.reset_password import MyPasswordResetForm, MySetPasswordForm
from portail.views.login import ClassCommuneLogin
from portail.utils import utils_secquest, utils_email


class MyPasswordResetView(ClassCommuneLogin, auth_views.PasswordResetView):
    email_template_name = "portail/password_reset/emails/confirmation_html.html"
    form_class = MyPasswordResetForm
    subject_template_name = "portail/password_reset/emails/confirmation_sujet.txt"
    success_url = reverse_lazy('password_reset_done')
    template_name = "portail/reset_password.html"

    def form_valid(self, form):
        identifiant = form.cleaned_data["identifiant"]
        email = form.cleaned_data["email"]
        logger.debug("Demande de reset du password : %s %s." % (identifiant, email))

        # Recherche l'utilisateur
        utilisateur = Utilisateur.objects.filter(username__iexact=identifiant, is_active=True, categorie="famille").first()
        if not utilisateur or not utilisateur.famille.mail or utilisateur.famille.mail != email:
            logger.debug("Erreur : Pas de compte actif existant.")
            form.add_error(None, "Il n'existe pas de compte actif correspondant à cet identifiant et cette adresse Email.")
            return self.render_to_response(self.get_context_data(form=form))

        opts = {
            "nom_template_sujet": "portail/password_reset/emails/confirmation_sujet.txt",
            "nom_template_html": "portail/password_reset/emails/confirmation_html.html",
            "nom_template_texte": "portail/password_reset/emails/confirmation_texte.html",
            "utilisateur": utilisateur, "request": self.request,
            "token": default_token_generator.make_token(utilisateur),
        }
        resultat = utils_email.Envoyer_email(**opts)

        # Génération du secquest
        utils_secquest.Generation_secquest(famille=utilisateur.famille)

        # Affiche l'erreur rencontrée dans le form
        if resultat != True:
            form.add_error(None, resultat)
            return super(MyPasswordResetView, self).form_invalid(form)

        return super().form_valid(form)


class MyPasswordResetDoneView(ClassCommuneLogin, auth_views.PasswordResetDoneView):
    template_name = "portail/password_reset/done.html"


class MyPasswordResetConfirmView(ClassCommuneLogin, auth_views.PasswordResetConfirmView):
    template_name = "portail/password_reset/confirm.html"
    form_class = MySetPasswordForm

    def form_valid(self, form):
        # Vérification de la secquest
        if "secquest" in form.cleaned_data:
            if not utils_secquest.Check_secquest(famille=self.user.famille, reponse=form.cleaned_data["secquest"]):
                form.add_error(None, "La réponse à la question est erronée")
                return self.render_to_response(self.get_context_data(form=form))

        return super().form_valid(form)


class MyPasswordResetCompleteView(ClassCommuneLogin, auth_views.PasswordResetCompleteView):
    template_name = "portail/password_reset/complete.html"
