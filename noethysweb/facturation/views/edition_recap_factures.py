# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from facturation.forms.edition_recap_factures import Formulaire


def Generer_pdf(request):
    time.sleep(1)

    # Récupération des options
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data

    # Validation des paramètres
    if options["type_selection"] == "LOT" and not options["lot"]:
        return JsonResponse({"erreur": "Vous devez sélectionner un lot de factures"}, status=401)

    # Récupération de la période de date d'édition
    options["date_edition"] = utils_dates.ConvertDateRangePicker(options["date_edition"])

    # Création du PDF
    from facturation.utils import utils_impression_recap_factures
    impression = utils_impression_recap_factures.Impression(titre="Edition du récapitulatif des factures", dict_donnees=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})


class View(CustomView, TemplateView):
    menu_code = "edition_recap_factures"
    template_name = "facturation/edition_recap_factures.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition du récapitulatif des factures"
        context['box_titre'] = "Edition du récapitulatif des factures"
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur le bouton Générer le PDF. La génération du document peut nécessiter quelques instants d'attente."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context
