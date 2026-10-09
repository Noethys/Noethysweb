# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.core.cache import cache
from core.utils import utils_parametres

NBRE_MAX_FAVORIS = 30


def Get_codes_favoris(options_interface={}):
    """ Renvoie la liste des codes des commandes favorites à partir des options d'interface """
    try:
        codes = json.loads(options_interface.get("menu_favoris", "[]") or "[]")
    except (ValueError, TypeError):
        codes = []
    return [code for code in codes if isinstance(code, str)]


def Get_commandes_favorites(menu_principal=None, codes=[]):
    """ Renvoie les objets Menu correspondant aux favoris (seules les commandes autorisées pour l'utilisateur sont renvoyées) """
    if not menu_principal:
        return []
    dict_commandes = {commande.code: commande for commande in menu_principal.GetCommandes()}
    return [dict_commandes[code] for code in codes if code in dict_commandes]


def Enregistrer_codes_favoris(utilisateur=None, codes=[]):
    utils_parametres.Set(nom="menu_favoris", categorie="options_interface", utilisateur=utilisateur, valeur=json.dumps(codes))
    cache.delete("options_interface_user%d" % utilisateur.pk)


def Modifier_affichage(request):
    """ Mémorise le type d'affichage des pages sommaires des menus (détaillé ou condensé) """
    condense = request.POST.get("condense", "") == "1"
    utils_parametres.Set(nom="menu_affichage_condense", categorie="options_interface", utilisateur=request.user, valeur=condense)
    cache.delete("options_interface_user%d" % request.user.pk)
    return JsonResponse({"condense": condense})


def Modifier_favoris(request):
    """ Ajout, suppression ou réorganisation des favoris de l'utilisateur """
    from core.views.menu import GetMenuPrincipal
    action = request.POST.get("action", "")
    organisateur = cache.get("organisateur")
    if not organisateur:
        from core.models import Organisateur
        organisateur = Organisateur.objects.filter(pk=1).first()
    menu_principal = GetMenuPrincipal(organisateur=organisateur, user=request.user)
    codes_autorises = {commande.code for commande in menu_principal.GetCommandes()}

    # Lecture des favoris actuels
    parametre = utils_parametres.Get(nom="menu_favoris", categorie="options_interface", utilisateur=request.user, valeur="[]")
    codes = Get_codes_favoris({"menu_favoris": parametre})

    if action in ("ajouter", "retirer"):
        code = request.POST.get("code", "")
        if action == "ajouter" and code not in codes_autorises:
            return JsonResponse({"erreur": "Cette commande n'est pas disponible"}, status=401)
        if action == "ajouter" and code not in codes:
            if len(codes) >= NBRE_MAX_FAVORIS:
                return JsonResponse({"erreur": "Vous ne pouvez pas avoir plus de %d favoris" % NBRE_MAX_FAVORIS}, status=401)
            codes.append(code)
        if action == "retirer" and code in codes:
            codes.remove(code)

    elif action == "ordonner":
        try:
            nouveaux_codes = json.loads(request.POST.get("codes", "[]"))
        except ValueError:
            return JsonResponse({"erreur": "Liste de favoris invalide"}, status=401)
        # On ne conserve que les codes valides, sans doublon
        codes = []
        for code in nouveaux_codes:
            if isinstance(code, str) and code in codes_autorises and code not in codes:
                codes.append(code)
        codes = codes[:NBRE_MAX_FAVORIS]

    else:
        return JsonResponse({"erreur": "Action inconnue"}, status=401)

    Enregistrer_codes_favoris(utilisateur=request.user, codes=codes)
    return JsonResponse({"favoris": codes})
