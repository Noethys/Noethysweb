# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib.auth.views import LoginView
from portail.forms.login import FormLoginFamille
from noethysweb.version import GetVersion
from core.models import Organisateur
from django.core.cache import cache
from django.contrib.auth.models import update_last_login
from core.utils import utils_portail


class ClassCommuneLogin:

    def get_context_data(self, **kwargs):
        context = super(ClassCommuneLogin, self).get_context_data(**kwargs)
        # Type de public
        context['public'] = "famille"

        # Version application
        context['version_application'] = cache.get_or_set('version_application', GetVersion())

        # Organisateur
        organisateur = cache.get('organisateur')
        if not organisateur:
            organisateur = Organisateur.objects.filter(pk=1).first()
            cache.set('organisateur', organisateur)
        context['organisateur'] = organisateur

        # Paramètres du portail
        parametres_portail = cache.get('parametres_portail')
        if not parametres_portail:
            parametres_portail = utils_portail.Get_dict_parametres()
            cache.set('parametres_portail', parametres_portail)
        context['parametres_portail'] = parametres_portail

        return context



class LoginViewFamille(ClassCommuneLogin, LoginView):
    form_class = FormLoginFamille
    template_name = 'portail/login.html'
    redirect_field_name = 'portail_accueil'

    def form_valid(self, form):
        update_last_login(None, form.get_user())
        return super(LoginViewFamille, self).form_valid(form)
