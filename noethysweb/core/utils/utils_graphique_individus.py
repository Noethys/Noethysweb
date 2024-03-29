# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.shortcuts import render
from django.http import JsonResponse
from core.models import Activite
from core.utils import utils_parametres


def Get_parametres(request):
    """ Récupère les paramètres du graphique """
    activites = Activite.objects.filter(structure__in=request.user.structures.all()).order_by("-date_fin", "nom")
    context = {"activites": activites}
    return render(request, "core/accueil/widgets/graphe_individus_parametres.html", context)

def Set_parametres(request):
    """ Mémorise les paramètres du graphique """
    idactivite = int(request.POST.get("idactivite"))
    utils_parametres.Set(nom="activite", categorie="graphique_individus", utilisateur=request.user, valeur=idactivite)
    return JsonResponse({"resultat": True})
