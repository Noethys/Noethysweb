# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import JsonResponse
from core.models import Vacance, Ferie
import datetime


def Get_calendrier(request):
    dict_resultats = {"vacances": {}, "feries": {}}

    # Vacances
    for vacance in Vacance.objects.all():
        dict_resultats["vacances"][vacance.idvacance] = {"date_debut": str(vacance.date_debut), "date_fin": str(vacance.date_fin)}

    # Fériés
    for ferie in Ferie.objects.all():
        dict_resultats["feries"]["%d-%02d-%02d" % (ferie.annee, ferie.mois, ferie.jour)] = None

    return JsonResponse(dict_resultats)


def Get_vacances(request):
    annee = int(request.POST.get('annee'))
    dict_resultats = {"vacances": []}

    for vacance in Vacance.objects.filter(date_debut__year=annee).order_by("date_debut"):
        dict_resultats["vacances"].append({"nom": vacance.nom, "date_debut": str(vacance.date_debut), "date_fin": str(vacance.date_fin)})
    return JsonResponse(dict_resultats)