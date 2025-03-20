# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.
import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from reglements.utils import utils_ventilation
from core.models import PortailParametre


def Verifie_ventilation(function):
    def _function(request, *args, **kwargs):
        if not request.GET.get("correction_ventilation", None):
            dict_anomalies = utils_ventilation.GetAnomaliesVentilation()
            if dict_anomalies:
                return HttpResponseRedirect(reverse_lazy("corriger_ventilation") + "?next=" + request.path)
        return function(request, *args, **kwargs)
    return _function


def secure_ajax(function):
    """ A associer aux requêtes AJAX """
    def _function(request, *args, **kwargs):
        # Vérifie que c'est une requête AJAX
        if not request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return HttpResponseBadRequest()
        # Vérifie que l'utilisateur est authentifié
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        # Vérifie que c'est un user de type utilisateur
        if request.user.categorie != "utilisateur":
            return HttpResponseForbidden()
        return function(request, *args, **kwargs)
    return _function


def secure_ajax_portail(function):
    """ A associer aux requêtes AJAX """
    def _function(request, *args, **kwargs):
        compte_famille = PortailParametre.objects.filter(code="compte_famille").first()
        compte_individu = PortailParametre.objects.filter(code="compte_individu").first()
        # logger.debug("compte_famille:  %s" % compte_famille.valeur)
        # logger.debug("compte_individu: %s" % compte_individu.valeur)
        # Vérifie que c'est une requête AJAX
        if not request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return HttpResponseBadRequest()
        # Vérifie que l'utilisateur est authentifié
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        # Vérifie que c'est un user de type utilisateur
        # et que si le paramètre de compte individu est true ( coché ) alors interdire l'accès ou l'utilisation des identifiants famille
        if((request.user.categorie not in ["famille", "individu"])  # Vérification de la catégorie : Si l'utilisateur n'est ni "famille" ni "individu", l'accès est interdit.
                or (compte_famille != "True" and request.user.categorie == "famille")   #Compte famille non activé pour une famille: Si compte_famille n'est pas "True" et que la catégorie est "famille", l'accès est interdit.
                or ( compte_individu == "True" and request.user.categorie == "famille")): #Compte individu activé pour une famille: Si compte_individu est "True" alors que l'utilisateur est de catégorie "famille", l'accès est interdit.
        # if request.user.categorie != "individu":
            return HttpResponseForbidden()
        return function(request, *args, **kwargs)
    return _function
