# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from facturation.forms.export_ecritures_quadra import Formulaire
from facturation.utils import utils_export_quadra


def Exporter(request):
    """ Générer le fichier d'export """
    # Récupération des options
    time.sleep(1)
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data

    # Exporter
    export = utils_export_quadra.Exporter(request=request, options=options)
    resultat = export.Generer()
    if not resultat:
        return JsonResponse({"erreurs": export.Get_erreurs_html()}, status=401)
    return JsonResponse({"resultat": "ok", "nom_fichier": resultat})


class View(CustomView, TemplateView):
    menu_code = "export_ecritures_quadra"
    template_name = "facturation/export_ecritures_quadra.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Export des écritures comptables"
        context['box_titre'] = "Export des écritures vers Quadra Compta"
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur le bouton Exporter."
        if "form" not in kwargs:
            context["form"] = Formulaire(request=self.request)
        return context
