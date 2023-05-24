# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.shortcuts import render
from django.contrib import messages
from django.views.generic import TemplateView
from core.models import Famille
from core.views.base import CustomView
from reglements.utils import utils_ventilation


class View(CustomView, TemplateView):
    menu_code = "corriger_ventilation"
    template_name = "reglements/corriger_ventilation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Ventilation"
        context['box_titre'] = "Corriger la ventilation"
        dict_anomalies = utils_ventilation.GetAnomaliesVentilation()
        context['box_introduction'] = "Vous pouvez corriger ici les anomalies de ventilation une par une en cliquant sur le bouton à droite de la liste ou de façon globale en cliquant sur le bouton Ventiler automatiquement.<br><br>"
        if len(dict_anomalies) == 1:
            context['box_introduction'] += "<i class='fa fa-exclamation-triangle text-warning margin-r-5'></i><b>1 anomalie de ventilation a été détectée. Il est recommandé de la corriger dès à présent.</b>"
        elif len(dict_anomalies) > 1:
            context['box_introduction'] += "<i class='fa fa-exclamation-triangle text-warning margin-r-5'></i><b>%d anomalies de ventilation ont été détectées. Il est recommandé de les corriger dès à présent.</b>" % len(dict_anomalies)
        else:
            context['box_introduction'] += "<i class='fa fa-check-circle-o text-green margin-r-5'></i><b>Aucune anomalie n'a été détectée</b>. "
        context['items'] = [{"famille": famille, "valeurs": dict_anomalies[famille.pk]} for famille in Famille.objects.filter(pk__in=dict_anomalies.keys()).order_by("nom")]
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        # Actualiser l'affichage
        if action == "actualiser":
            return render(request, self.template_name, self.get_context_data(**kwargs))

        # Récupère la lise des sélections
        try:
            liste_familles = json.loads(request.POST.get('selections'))
        except:
            liste_familles = []

        # Vérifie qu'au moins une ligne a été cochée
        if len(liste_familles) == 0:
            messages.add_message(self.request, messages.ERROR, "Vous n'avez coché aucune ligne !")
            return render(request, self.template_name, self.get_context_data(**kwargs))

        # Ventilation automatique
        for IDfamille in liste_familles:
            utils_ventilation.Ventilation_auto(IDfamille=IDfamille)

        return render(request, self.template_name, self.get_context_data(**kwargs))
