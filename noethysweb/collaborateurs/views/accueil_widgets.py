# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Rechargement des widgets collaborateurs de la page d'accueil lors d'un changement de date """

from django.http import HttpResponseForbidden
from django.shortcuts import render
from collaborateurs.utils import utils_accueil, utils_planning


def Get_equipe_du_jour(request):
    if not request.user.has_perm(utils_planning.PERMISSION):
        return HttpResponseForbidden()
    date = utils_accueil.Lire_date(request.POST.get("date"))
    context = {"collaborateurs_equipe_du_jour": utils_accueil.Get_equipe_du_jour(user=request.user, date=date)}
    return render(request, "collaborateurs/accueil/equipe_du_jour_contenu.html", context)


def Get_encadrement(request):
    if not request.user.has_perm(utils_planning.PERMISSION):
        return HttpResponseForbidden()
    date = utils_accueil.Lire_date(request.POST.get("date"))
    context = {"collaborateurs_encadrement": utils_accueil.Get_encadrement(date=date)}
    return render(request, "collaborateurs/accueil/encadrement_contenu.html", context)
