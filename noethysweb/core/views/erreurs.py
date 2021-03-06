# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.shortcuts import render

def erreur_403(request, exception=None):
    return render(request, "core/erreurs/erreur_403.html")

def erreur_404(request, exception=None):
    return render(request, "core/erreurs/erreur_404.html")

def erreur_500(request, exception=None):
    return render(request, "core/erreurs/erreur_500.html")

def erreur_axes(request, exception=None):
    return render(request, "core/erreurs/erreur_axes.html")
