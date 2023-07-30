# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.conf import settings

def erreur_403(request, exception=None):
    return render(request, "core/erreurs/erreur_403.html")

def erreur_404(request, exception=None):
    return render(request, "core/erreurs/erreur_404.html")

def erreur_500(request, exception=None):
    return render(request, "core/erreurs/erreur_500.html")

def erreur_axes(request, exception=None):
    return render(request, "core/erreurs/erreur_axes.html")

def deblocage(request, code=None):
    if code.lower() == settings.URL_GESTION.lower().replace("/", "")[-10:]:
        logger.debug("Demande de reset axes par code")
        from axes.utils import reset
        reset()
        return render(request, "core/erreurs/deblocage.html")
    return render(request, "core/erreurs/erreur_500.html")
