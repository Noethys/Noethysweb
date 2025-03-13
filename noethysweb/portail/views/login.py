# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.core.cache import cache
from django.templatetags.static import static
from django.contrib.auth.models import update_last_login
from noethysweb.version import GetVersion
from core.models import Organisateur, ImageFond
from core.utils import utils_portail, utils_historique
from portail.forms.login import FormLogin


class ClassCommuneLogin:

    def get_context_data(self, **kwargs):
        context = super(ClassCommuneLogin, self).get_context_data(**kwargs)
        # Type de public
        context['public'] = ["famille", "individu"]


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

        # Recherche de l'image de fond
        idimage_fond = parametres_portail.get("connexion_image_fond", None)
        if idimage_fond:
            context['url_image_fond'] = ImageFond.objects.filter(pk=idimage_fond).first().image.url
        else:
            context['url_image_fond'] = static("images/portail.jpg")

        return context

class LoginViewGeneric(ClassCommuneLogin, LoginView):
    form_class = FormLogin
    template_name = 'portail/login.html'  # Vous pouvez utiliser le même template si c'est approprié
    redirect_field_name = 'portail_accueil'  # Redirigez vers l'accueil de l'utilisateur individuel

    def form_valid(self, form):
        # Enregistre la date de la dernière connexion
        update_last_login(None, form.get_user())
        # Enregistre la connexion dans le log
        logger.debug("Connexion portail %s" % form.get_user())
        user=form.get_user()
        logger.debug("User: %s" % user)

        if user is not None:
        # Déterminer s'il s'agit d'un utilisateur famille ou individu
            if user.username.startswith("F"):  # Supposons que les utilisateurs famille ont l'attribut `famille`
                print('FFFFF')

                utils_historique.Ajouter(
                        titre="Connexion au portail individuel",
                        utilisateur=user,
                        famille=user.famille.pk,
                        portail=True
                )
            elif  user.username.startswith("I"):
                utils_historique.Ajouter(
                    titre="Connexion au portail individuel",
                    utilisateur=user,
                    individu=user.individu.pk,
                    portail=True
                )

        return super(LoginViewGeneric, self).form_valid(form)

    def get_success_url(self):
        next = self.get_redirect_url()
        return next or reverse_lazy("portail_accueil")
