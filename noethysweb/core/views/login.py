# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.core.cache import cache
from django.contrib.auth.models import update_last_login
from django.templatetags.static import static
from noethysweb.version import GetVersion
from core.forms.login import FormLoginUtilisateur
from core.models import Organisateur


class ClassCommuneLogin:

    def get_context_data(self, **kwargs):
        context = super(ClassCommuneLogin, self).get_context_data(**kwargs)
        # Type de public
        context['public'] = "utilisateur"

        # Version application
        context['version_application'] = cache.get_or_set('version_application', GetVersion())

        # Organisateur
        organisateur = cache.get('organisateur')
        if not organisateur:
            organisateur = Organisateur.objects.filter(pk=1).first()
            cache.set('organisateur', organisateur)
        context['organisateur'] = organisateur

        # Recherche de l'image de fond
        context['url_image_fond'] = static("images/bureau.jpg")

        return context



class LoginViewUtilisateur(ClassCommuneLogin, LoginView):
    form_class = FormLoginUtilisateur
    template_name = 'core/login.html'
    redirect_field_name = 'accueil'

    def form_valid(self, form):
        update_last_login(None, form.get_user())
        # Enregistre la connexion dans le log
        logger.debug("Connexion de l'utilisateur %s" % form.get_user())
        return super(LoginViewUtilisateur, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy("accueil")
