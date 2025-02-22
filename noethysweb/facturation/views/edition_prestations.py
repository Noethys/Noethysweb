# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from facturation.forms.edition_prestations import Formulaire


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
    date_debut = utils_dates.ConvertDateENGtoDate(options["periode"].split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(options["periode"].split(";")[1])
    options["periode"] = (date_debut, date_fin)

    # Création du PDF
    from facturation.utils import utils_impression_prestations
    impression = utils_impression_prestations.Impression(titre="Edition des prestations", dict_donnees=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    time.sleep(1)
    return JsonResponse({"nom_fichier": nom_fichier})


class View(CustomView, TemplateView):
    menu_code = "edition_prestations"
    template_name = "core/edition_pdf.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition des prestations"
        context['box_titre'] = "Edition des prestations"
        context['url_ajax_edition_pdf'] = "ajax_edition_prestations_generer_pdf"
        context['id_form'] = "form_parametres"
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur le bouton Générer le PDF. La génération du document peut nécessiter quelques instants d'attente."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context
