# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from individus.forms.edition_informations import Formulaire


def Generer_pdf(request):
    # Récupération des options
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data

    # Récupération des paramètres
    options["activites"] = json.loads(options["activites"])
    if not options["activites"]["ids"]:
        return JsonResponse({"erreur": "Veuillez cocher au moins une activité"}, status=401)

    # Récupération de la période
    if options["presents"]:
        presents = options.get("presents")
        date_debut = utils_dates.ConvertDateENGtoDate(presents.split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(presents.split(";")[1])
        options["presents"] = (date_debut, date_fin)

    # Création du PDF
    from individus.utils import utils_impression_informations
    impression = utils_impression_informations.Impression(titre="Edition des informations et régimes", dict_donnees=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    time.sleep(1)
    return JsonResponse({"nom_fichier": nom_fichier})


class View(CustomView, TemplateView):
    menu_code = "edition_informations"
    template_name = "individus/edition_informations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition des informations et régimes"
        context['box_titre'] = "Edition des informations et régimes"
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur le bouton Générer le PDF. La génération du document peut nécessiter quelques instants d'attente."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context
