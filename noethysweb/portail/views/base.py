# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from portail.views.menu import GetMenuPrincipal
from noethysweb.version import GetVersion
from core.models import Organisateur, Parametre
from django.core.cache import cache
from core.utils import utils_parametres, utils_portail


class CustomView(LoginRequiredMixin, UserPassesTestMixin):
    """ Implémente les données de la page : menus..."""
    menu_code = ""

    # Connexion obligatoire
    login_url = 'portail_connexion'
    redirect_field_name = 'portail_accueil'

    def test_func(self):
        # # Vérifie que l'user a une permission
        # menu_code = getattr(self, "menu_code", None)
        # if menu_code and menu_code != "accueil" and not menu_code.endswith("_toc"):
        #     if not menu_code and hasattr(self, "url_liste"):
        #         menu_code = self.url_liste
        #     if not self.request.user.has_perm("core.%s" % menu_code):
        #         return False

        # Vérifie que l'user est de type "utilisateur"
        if self.request.user.categorie != "famille":
            return False
        return True

    def get_context_data(self, **kwargs):
        context = super(CustomView, self).get_context_data(**kwargs)

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
            cache.set('parametres_portail', parametres_portail, 30)
        context['parametres_portail'] = parametres_portail

        # Options d'interface
        if cache.get('options_interface', None) != None:
            context['options_interface'] = cache.get('options_interface', {})
        else:
            defaut = {
                "dark-mode": False,
                "masquer-sidebar": False,
                "text-sm": True,
                "sidebar-no-expand": True,
            }
            parametres = utils_parametres.Get_categorie(categorie='options_interface', utilisateur=self.request.user, parametres=defaut)
            context['options_interface'] = parametres
            cache.set('options_interface', parametres)

        # Mémorise le menu principal
        menu_principal = GetMenuPrincipal(parametres_portail=parametres_portail, user=self.request.user)
        context['menu_principal'] = menu_principal

        # Si la page est un crud, on récupère l'url de la liste en tant que menu_code
        if not self.menu_code and hasattr(self, "url_liste"):
            self.menu_code = self.url_liste

        # Mémorise le menu actif
        menu_actif = menu_principal.Find(code=self.menu_code)
        context['menu_actif'] = menu_actif

        # Mémorise le fil d'ariane
        if context['menu_actif'] != None:
            context['breadcrumb'] = context['menu_actif'].GetBreadcrumb()

        return context
