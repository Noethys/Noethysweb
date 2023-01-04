# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Q
from core.views.base import CustomView
from core.models import Vacance, Ferie


def Get_calendrier_annuel(request):
    """ Renvoie les jours du calendrier annuel """
    annee = int(request.POST.get("annee"))
    events = []
    # Périodes de vacances
    for vacance in Vacance.objects.filter(date_fin__gte=datetime.date(annee, 1, 1), date_debut__lte=datetime.date(annee, 12, 31)):
        events.append({
            "debut": [vacance.date_debut.year, vacance.date_debut.month-1, vacance.date_debut.day],
            "fin": [vacance.date_fin.year, vacance.date_fin.month-1, vacance.date_fin.day],
            "color": "#faffc9"
        })
    # Jours fériés
    for ferie in Ferie.objects.filter(Q(annee=annee) | Q(annee=0)):
        events.append({
            "debut": [annee, ferie.mois-1, ferie.jour],
            "fin": [annee, ferie.mois-1, ferie.jour],
            "color": "#eaeaea"
        })
    return JsonResponse(events, safe=False)


class View(CustomView, TemplateView):
    template_name = "outils/calendrier_annuel.html"
    menu_code = "calendrier_annuel"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Calendrier annuel"
        context['box_titre'] = ""
        context['box_introduction'] = "Ce calendrier annuel vous permet notamment de vérifier si les périodes de vacances et les jours fériés ont bien été paramétrés."
        return context
