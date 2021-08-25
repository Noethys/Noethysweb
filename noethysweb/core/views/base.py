# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from core.views.menu import GetMenuPrincipal
from noethysweb.version import GetVersion
from core.models import Organisateur, Parametre, Utilisateur, PortailMessage
from django.core.cache import cache
from core.utils import utils_parametres
from django.http import JsonResponse
from django.conf import settings
import json


def Memorise_option(request):
    """ Mémorise dans la DB et le cache une option d'interface pour l'utilisateur"""
    nom = request.POST.get("nom")
    valeur = json.loads(request.POST.get("valeur"))
    utils_parametres.Set(nom=nom, categorie="options_interface", utilisateur=request.user, valeur=valeur)
    cache.delete('options_interface')
    return JsonResponse({"success": True})


# def Memorise_structure(request):
#     """ Mémorise dans la DB la structure actuelle de l'utilisateur """
#     idstructure = request.POST.get("idstructure")
#     request.user.structure_actuelle_id = idstructure
#     request.user.save()
#     return JsonResponse({"success": True})



class CustomView(LoginRequiredMixin, UserPassesTestMixin): #, PermissionRequiredMixin):
    """ Implémente les données de la page : menus..."""
    menu_code = ""
    compatible_demo = True

    # Connexion obligatoire
    login_url = 'connexion'
    redirect_field_name = 'accueil'

    def test_func(self):
        # Vérifie que l'user a une permission
        menu_code = getattr(self, "menu_code", None)
        if menu_code and menu_code != "accueil" and not menu_code.endswith("_toc"):
            if not menu_code and hasattr(self, "url_liste"):
                menu_code = self.url_liste
            if not self.request.user.has_perm("core.%s" % menu_code):
                return False

        # Vérifie que l'user est de type "utilisateur"
        if self.request.user.categorie != "utilisateur":
            return False

        # Vérifie que cette fonction est compatible avec le mode DEMO
        if not self.compatible_demo and settings.MODE_DEMO:
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

        # Options d'interface
        key_cache = "options_interface_user%d" % self.request.user.pk
        if cache.get(key_cache, None) != None:
            context['options_interface'] = cache.get(key_cache, {})
        else:
            defaut = {
                "dark-mode": False,
                "masquer-sidebar": False,
                "text-sm": True,
                "sidebar-no-expand": True,
            }
            parametres = utils_parametres.Get_categorie(categorie='options_interface', utilisateur=self.request.user, parametres=defaut)
            context['options_interface'] = parametres
            cache.set(key_cache, parametres)

        # Mémorise le menu principal
        menu_principal = GetMenuPrincipal(organisateur=organisateur, user=self.request.user)
        context['menu_principal'] = menu_principal

        # Si la page est un crud, on récupère l'url de la liste en tant que menu_code
        if not self.menu_code and hasattr(self, "url_liste"):
            self.menu_code = self.url_liste

        # Mémorise le menu actif
        menu_actif = menu_principal.Find(code=self.menu_code)
        context['menu_actif'] = menu_actif
        if menu_actif:
            context['menu_brothers'] = menu_actif.GetBrothers()
        context['afficher_menu_brothers'] = False

        # Mémorise le fil d'ariane
        if context['menu_actif'] != None:
            context['breadcrumb'] = context['menu_actif'].GetBreadcrumb()

        # Messages du portail non lus
        context["liste_messages_non_lus"] = PortailMessage.objects.select_related("famille", "structure").filter(structure__in=self.request.user.structures.all(), utilisateur__isnull=True, date_lecture__isnull=True).order_by("date_creation")

        return context

