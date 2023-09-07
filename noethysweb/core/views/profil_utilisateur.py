# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, time
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib import messages
from core.views.base import CustomView


def Purger_filtres_listes(request):
    """ Supprime tous les filtres de listes de l'utilisateur """
    time.sleep(2)
    from core.models import FiltreListe
    FiltreListe.objects.filter(utilisateur=request.user).delete()
    messages.add_message(request, messages.SUCCESS, "Tous les filtres de listes de l'utilisateur ont été supprimés")
    return JsonResponse({"url": reverse_lazy("profil_utilisateur")})


class View(CustomView, TemplateView):
    menu_code = "accueil"
    template_name = "core/profil.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Profil"
        context['box_titre'] = "Profil de l'utilisateur"
        context['box_introduction'] = ""
        return context
