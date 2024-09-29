# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from facturation.forms.export_ecritures_cloe import Formulaire
from facturation.utils import utils_export_cloe


def Exporter(request):
    """ Générer le fichier d'export """
    # Récupération des options
    time.sleep(1)
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data

    # Exporter
    export = utils_export_cloe.Exporter(request=request, options=options)
    resultat = export.Generer()
    if not resultat:
        return JsonResponse({"erreurs": export.Get_erreurs_html()}, status=401)
    return JsonResponse({"resultat": "ok", "nom_fichier": resultat})


class View(CustomView, TemplateView):
    menu_code = "export_ecritures_cloe"
    template_name = "facturation/export_ecritures_cloe.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Export des écritures vers Cloé"
        context['box_titre'] = "Export des écritures vers Cloé"
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur le bouton Exporter."
        context["formats_export"] = [
            ("Comptes clients", utils_export_cloe.format_export_cpt),
            ("Factures", utils_export_cloe.format_export_fac),
            ("Règlements", utils_export_cloe.format_export_rgl),
        ]
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context
