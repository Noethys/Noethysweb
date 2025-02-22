# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from reglements.forms.edition_ventilations_reglements import Formulaire


def Generer_pdf(request):
    time.sleep(1)

    # Récupération des options
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data
    options["periode"] = utils_dates.ConvertDateRangePicker(options["periode"])

    # Création du PDF
    from reglements.utils import utils_impression_ventilations_reglements
    impression = utils_impression_ventilations_reglements.Impression(titre="Edition des ventilations des règlements", dict_donnees=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})


class View(CustomView, TemplateView):
    menu_code = "edition_ventilations_reglements"
    template_name = "core/edition_pdf.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition des ventilations des règlements"
        context['box_titre'] = "Edition des ventilations des règlements"
        context['url_ajax_edition_pdf'] = "ajax_edition_ventilations_reglements_generer_pdf"
        context['id_form'] = "form_parametres"
        context['box_introduction'] = "Vous pouvez obtenir ici un PDF détaillant pour chaque règlement les prestations associées. Renseignez les paramètres et cliquez sur le bouton Générer le PDF. La génération du document peut nécessiter quelques instants d'attente."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context
