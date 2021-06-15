# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib import messages
from outils.utils import utils_update
from django.core.cache import cache


class View(CustomView, TemplateView):
    template_name = "outils/update.html"
    menu_code = "update"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Mise à jour de l'application"
        version_disponible, changelog = utils_update.Recherche_update()
        context['version_disponible'] = version_disponible
        context['changelog'] = changelog
        return context

    def post(self, request):
        # Lance la mise à jour
        resultat = utils_update.Update()

        # Supprime du cache la dernière recherche de mise à jour
        cache.delete('last_check_update')

        # Vérifie qu'au moins une réponse a été cochée
        if resultat == True:
            messages.add_message(self.request, messages.SUCCESS, "Mise à jour effectuée avec succès")
        else:
            messages.add_message(self.request, messages.ERROR, "Echec de la mise à jour")

        return HttpResponseRedirect(reverse_lazy("update"))
