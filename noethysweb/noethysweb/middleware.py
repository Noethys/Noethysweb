# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import HttpResponseRedirect
from django.urls import reverse
from portail.utils import utils_secquest
from core.models import Famille

from core.models import PortailParametre


class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 🔹 Initialisation des paramètres de compte utilisateur dans la session
        if 'compte_individu_active' not in request.session or 'compte_famille_active' not in request.session:
            compte_individu = PortailParametre.objects.filter(code="compte_individu").first()
            compte_famille = PortailParametre.objects.filter(code="compte_famille").first()

            request.session['compte_individu_active'] = bool(compte_individu and compte_individu.valeur == 'True')
            request.session['compte_famille_active'] = bool(compte_famille and compte_famille.valeur == 'True')

            request.session.modified = True  # 🔹 Assure que Django met bien à jour la session

        response = self.get_response(request)

        # URL pour changer le mot de passe
        url_change_password = reverse("password_change")

        # Oblige la famille ou l'individu à changer son mot de passe
        if request.user.is_authenticated:
            # Vérification pour les utilisateurs de type famille
            if request.user.categorie == "famille" and request.user.force_reset_password and request.path != url_change_password:
                utils_secquest.Generation_secquest(famille=request.user.famille)
                return HttpResponseRedirect(url_change_password)

            # Vérification pour les utilisateurs de type individu
            elif request.user.categorie == "individu" and request.user.force_reset_password and request.path != url_change_password:
                famille = Famille.objects.filter(titulaire_helios_id=request.user.individu).first()
                if famille:
                    utils_secquest.Generation_secquest(famille=famille)  # Génération de la question de sécurité pour la famille associée
                return HttpResponseRedirect(url_change_password)

        return response
