# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import HttpResponseRedirect
from django.urls import reverse
from portail.utils import utils_secquest


class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Oblige la famille à changer son mot de passe
        url_change_password = reverse("password_change")
        if request.user.is_authenticated and request.user.categorie == "famille" and request.user.force_reset_password and request.path != url_change_password:
            utils_secquest.Generation_secquest(famille=request.user.famille)
            return HttpResponseRedirect(url_change_password)

        return response
