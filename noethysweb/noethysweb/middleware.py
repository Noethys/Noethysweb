# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.urls import reverse
from portail.utils import utils_secquest


class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Oblige la famille ou le collaborateur à changer son mot de passe provisoire.
        # Le contrôle est fait AVANT l'exécution de la vue : sinon une action (requête AJAX, envoi de formulaire...)
        # serait exécutée avec le mot de passe provisoire avant que la réponse ne soit remplacée par la redirection.
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.categorie in ("famille", "collaborateur") and user.force_reset_password:
            url_change_password = reverse("password_change")
            if request.path not in (url_change_password, reverse("portail_deconnexion")):
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return HttpResponseForbidden()
                if user.categorie == "famille":
                    utils_secquest.Generation_secquest(famille=user.famille)
                return HttpResponseRedirect(url_change_password)

        return self.get_response(request)
