# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json
logger = logging.getLogger(__name__)
from django.db import models
from django.db.models.query import QuerySet
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.cache import cache
from django.shortcuts import redirect
from portail.views.menu import GetMenuPrincipal
from noethysweb.version import GetVersion
from core.models import Organisateur, Parametre
from core.utils import utils_parametres, utils_portail, utils_historique


class CustomView(LoginRequiredMixin, UserPassesTestMixin):
    """ Implémente les données de la page : menus..."""
    menu_code = ""

    # Connexion obligatoire
    login_url = 'portail_connexion'
    redirect_field_name = 'portail_accueil'

    def dispatch(self, request, *args, **kwargs):
        """ Vérifie que l'utilisateur est connecté """
        if not request.user.is_authenticated:
            return redirect("portail_connexion")
        return super(CustomView, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        # # Vérifie que l'user a une permission
        # menu_code = getattr(self, "menu_code", None)
        # if menu_code and menu_code != "accueil" and not menu_code.endswith("_toc"):
        #     if not menu_code and hasattr(self, "url_liste"):
        #         menu_code = self.url_liste
        #     if not self.request.user.has_perm("core.%s" % menu_code):
        #         return False

        # Vérifie que l'user est de type "utilisateur"
        if self.request.user.categorie not in  ["famille","individu"]:
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

    def Formate_historique(self, valeur=None):
        # Transforme une instance de model en pk
        if isinstance(valeur, (models.Model, models.base.ModelBase)):
            valeur = str(valeur)

        # Transforme les queryset en liste de pk
        if isinstance(valeur, QuerySet):
            valeur = ", ".join([str(instance) for instance in valeur.all()])

        # Transforme une liste d'instances en liste de pk
        if isinstance(valeur, list):
            valeur = ", ".join([str(item) if "models" in str(type(item)) else item for item in valeur])

        # Transforme la valeur en json
        return valeur

    def save_historique(self, instance=None, titre=None, detail=None, form=None):
        old = None

        # Titre
        if not titre:
            if hasattr(self, "Get_titre_historique"):
                titre = self.Get_titre_historique(instance)
            elif hasattr(self, "titre_historique"):
                titre = getattr(self, "titre_historique")
            else:
                titre = "%s %s" % (self.verbe_action, getattr(self, "objet_singulier", ""))

        # Détail
        if not detail:
            if hasattr(self, "Get_detail_historique"):
                detail = self.Get_detail_historique(instance)
            elif hasattr(self, "detail_historique"):
                detail = getattr(self, "detail_historique", str(instance)).format(instance)
            else:
                details = []
                anciennes_valeurs = []
                if form:
                    for nom_champ in form.changed_data:
                        try:
                            label_champ = form.instance._meta.get_field(nom_champ).verbose_name
                            valeur_champ = getattr(form.instance, nom_champ)
                            details.append("%s=%s" % (label_champ, valeur_champ))
                            anciennes_valeurs.append("%s=%s" % (label_champ, self.Formate_historique(form.initial.get(nom_champ, None))))
                        except:
                            pass
                else:
                    details.append(str(instance))
                detail = ", ".join(details)
                old = ", ".join(anciennes_valeurs)

        utilisateur = self.request.user
        objet = instance._meta.verbose_name.capitalize()
        idobjet = instance.pk
        classe = instance._meta.object_name
        famille = getattr(instance, "famille_id", None)
        if classe == "Famille":
            famille = instance.pk
        individu = getattr(instance, "individu_id", None)
        if classe == "Individu":
            individu = instance.pk
        utils_historique.Ajouter(titre=titre, detail=detail, old=old, utilisateur=utilisateur, famille=famille, individu=individu, objet=objet, idobjet=idobjet, classe=classe, portail=True)

        # Ecriture dans le log
        if famille:
            detail += " Famille=%s" % famille
        logger.debug("%s : %s (%s)" % (utilisateur, titre, detail))
        if individu:
            detail += " Individu=%s" % individu
        logger.debug("%s : %s (%s)" % (utilisateur, titre, detail))

