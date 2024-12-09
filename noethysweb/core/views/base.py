# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
from core.views.menu import GetMenuPrincipal
from core.models import Organisateur, Consommation, PortailMessage, PortailRenseignement
from core.utils import utils_parametres
from noethysweb.version import GetVersion


def Memorise_option(request):
    """ Mémorise dans la DB et le cache une option d'interface pour l'utilisateur """
    nom = request.POST.get("nom")
    valeur = json.loads(request.POST.get("valeur"))
    utils_parametres.Set(nom=nom, categorie="options_interface", utilisateur=request.user, valeur=valeur)
    cache.delete("options_interface_user%d" % request.user.pk)
    return JsonResponse({"success": True})

def Memorise_parametre(request):
    """ Mémorise un paramètre dans la DB """
    nom = request.POST.get("nom")
    categorie = request.POST.get("categorie")
    valeur = json.loads(request.POST.get("valeur"))
    utils_parametres.Set(nom=nom, categorie=categorie, utilisateur=request.user, valeur=valeur)
    return JsonResponse({"success": True})

def Memorise_tri_liste(request):
    """ Mémorise le tri d'une liste """
    colonne = request.POST.get("colonne")
    sens = request.POST.get("sens")
    nom_view = request.POST.get("view")
    nom_view = nom_view[4:nom_view.find(" object at ")]
    nom_view = nom_view.replace(".Liste", "")
    if colonne:
        utils_parametres.Set(nom=nom_view, categorie="tri_liste", utilisateur=request.user, valeur="%s;%s" % (colonne, sens))
    return JsonResponse({"success": True})

def Memorise_hidden_columns(request):
    """ Mémorise les colonnes cachées """
    colonnes = request.POST.get("colonnes")
    nom_view = request.POST.get("view")
    nom_view = nom_view[4:nom_view.find(" object at ")]
    nom_view = nom_view.replace(".Liste", "")
    utils_parametres.Set(nom=nom_view, categorie="hidden_columns", utilisateur=request.user, valeur=colonnes)
    return JsonResponse({"success": True})

def Memorise_page_length(request):
    """ Mémorise le page_length """
    page_length = request.POST.get("page_length")
    nom_view = request.POST.get("view")
    nom_view = nom_view[4:nom_view.find(" object at ")]
    nom_view = nom_view.replace(".Liste", "")
    utils_parametres.Set(nom=nom_view, categorie="page_length", utilisateur=request.user, valeur=page_length)
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
                logger.debug("Interdiction d'accéder à la page 'core.%s' : Pas de permission." % menu_code)
                return False

        # Vérifie que l'user est de type "utilisateur"
        if self.request.user.categorie != "utilisateur":
            logger.debug("Interdiction d'accéder à cette page : L'utilisateur n'est pas de type 'utilisateur'.")
            return False

        # Vérifie que cette fonction est compatible avec le mode DEMO
        if not self.compatible_demo and settings.MODE_DEMO:
            logger.debug("Interdiction d'accéder à cette page : Fonction incompatible avec le mode démo.")
            return False

        # Vérification spéciale d'une page
        if hasattr(self, "test_func_page"):
            if not self.test_func_page():
                logger.debug("Interdiction d'accéder à la page '%s' : Pas de permission pour cette donnée." % getattr(self, "menu_code", None))
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
                "configuration_accueil": json.dumps(settings.CONFIG_ACCUEIL_DEFAUT),
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

        # Mode démo
        context['mode_demo'] = settings.MODE_DEMO

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

        # Renseignements à traiter
        renseignements_attente = {validation_auto: nbre for validation_auto, nbre in PortailRenseignement.objects.filter(etat="ATTENTE").values_list("validation_auto").annotate(nbre=Count("pk"))}
        context["nbre_renseignements_attente_validation"] = renseignements_attente.get(False, 0)
        context["nbre_renseignements_attente_lecture"] = renseignements_attente.get(True, 0)

        # Demandes de réservations à traiter
        context["nbre_demandes_attente_traitement"] = Consommation.objects.values("date_saisie").filter(etat="demande", activite__structure__in=self.request.user.structures.all()).distinct().count()

        return context

