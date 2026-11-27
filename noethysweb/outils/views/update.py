# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from core.views.base import CustomView
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from outils.utils import utils_update
from django.core.cache import cache
from noethysweb import version
import datetime


class View(CustomView, TemplateView):
    template_name = "outils/update.html"
    menu_code = "update"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Mise à jour de l'application"
        version_disponible, changelog = utils_update.Recherche_update()
        version_installee = version.GetVersion()
        context['version_disponible'] = version_disponible
        context['version_installee'] = version_installee
        context['erreur_recherche'] = not changelog
        context['date_verification'] = datetime.datetime.now()

        # Changements : versions à installer, ou à défaut ceux de la version installée
        liste_versions, totaux = [], {}
        if changelog:
            if version_disponible:
                liste_versions, totaux = utils_update.Analyser_changelog(changelog, version_mini=version_installee)
            else:
                liste_versions, totaux = utils_update.Analyser_changelog(changelog, nbre_versions=1)
        context['liste_versions'] = liste_versions
        context['totaux'] = totaux
        return context

    def post(self, request):
        # Lance la mise à jour
        resultat = utils_update.Update()

        # Supprime du cache la dernière recherche de mise à jour
        cache.delete('last_check_update')
        cache.delete('last_check_update_user%d' % request.user.pk)

        if resultat == True:
            messages.add_message(self.request, messages.SUCCESS, "Mise à jour effectuée avec succès")
        else:
            messages.add_message(self.request, messages.ERROR, "Echec de la mise à jour")

        return HttpResponseRedirect(reverse_lazy("update"))


def Masquer_alerte_accueil(request):
    """ Masque l'encart de mise à jour de la page d'accueil jusqu'au lendemain """
    utils_update.Masquer_alerte_accueil(request=request)
    return JsonResponse({"succes": True})
