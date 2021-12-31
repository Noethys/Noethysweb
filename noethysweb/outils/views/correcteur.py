# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from django.db.models.functions import Concat
from django.db.models import Count, F, CharField, Value
from core.views.base import CustomView
from core.models import Consommation, Prestation


class View(CustomView, TemplateView):
    template_name = "outils/correcteur.html"
    menu_code = "correcteur"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Correcteur d'anomalies"
        context['box_titre'] = ""
        context['box_introduction'] = "Voici la liste des anomalies détectées dans les données."
        context['anomalies'] = self.Get_anomalies()
        return context

    def Get_anomalies(self):
        data = {}

        # Recherche les doublons dans les consommations (pour un individu sur une même date avec la même unité)
        qs = Consommation.objects.select_related("individu").annotate(doublon_id=Concat(F("individu_id"), Value("_"), F("inscription_id"), Value("_"), F("unite_id"), Value("_"), F("date"), output_field=CharField()))
        doublons = qs.values("individu__nom", "individu__prenom", "date", "doublon_id").annotate(nbre_doublons=Count("doublon_id")).filter(nbre_doublons__gt=1)
        data["Doublons de consommations"] = ["%s %s : %d doublons le %s." % (d["individu__nom"], d["individu__prenom"], d["doublon_id"], d["date"]) for d in doublons]

        # Recherche les doublons dans les prestations (pour un individu sur une même date avec le même tarif de prestation)
        qs = Prestation.objects.select_related("individu").annotate(doublon_id=Concat(F("individu_id"), Value("_"), F("famille_id"), Value("_"), F("tarif_id"), Value("_"), F("date"), output_field=CharField()))
        doublons = qs.values("individu__nom", "individu__prenom", "date", "doublon_id").annotate(nbre_doublons=Count("doublon_id")).filter(nbre_doublons__gt=1)
        data["Doublons de prestations"] = ["%s %s : %d doublons le %s." % (d["individu__nom"], d["individu__prenom"], d["doublon_id"], d["date"]) for d in doublons]

        return data
