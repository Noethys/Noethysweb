# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from core.views.menu import GetMenuPrincipal
from noethysweb.version import GetVersion
from core.models import Organisateur, Parametre
from django.core.cache import cache
from core.utils import utils_parametres
from django.http import JsonResponse



def Set_masquer_sidebar(request):
    """ Mémorise dans la DB et le cache le choix sidebar_collapse pour l'utilisateur"""
    masquer_sidebar = False if request.POST.get("masquer_sidebar") == "true" else True
    utils_parametres.Set(categorie="interface", nom="masquer_sidebar", utilisateur=request.user, valeur=masquer_sidebar)
    cache.set('masquer_sidebar', masquer_sidebar)
    return JsonResponse({"success": True})


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

        # Sidebar
        if cache.get('masquer_sidebar', None) != None:
            context['masquer_sidebar'] = cache.get('masquer_sidebar', None)
        else:
            parametre = utils_parametres.Get(categorie="interface", nom="masquer_sidebar", utilisateur=self.request.user, valeur=False)
            context['masquer_sidebar'] = parametre
            cache.set('masquer_sidebar', parametre)


        # # Mémorise le menu principal
        # menu_principal = GetMenuPrincipal(organisateur=organisateur, user=self.request.user)
        # context['menu_principal'] = menu_principal
        #
        # # Si la page est un crud, on récupère l'url de la liste en tant que menu_code
        # if not self.menu_code and hasattr(self, "url_liste"):
        #     self.menu_code = self.url_liste
        #
        # # Mémorise le menu actif
        # menu_actif = menu_principal.Find(code=self.menu_code)
        # context['menu_actif'] = menu_actif
        # if menu_actif:
        #     context['menu_brothers'] = menu_actif.GetBrothers()
        # context['afficher_menu_brothers'] = False
        #
        # # Mémorise le fil d'ariane
        # if context['menu_actif'] != None:
        #     context['breadcrumb'] = context['menu_actif'].GetBreadcrumb()

        return context

