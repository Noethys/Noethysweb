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
from outils.utils import utils_impression_calendrier_annuel


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


def Get_annee_scolaire_courante():
    aujourdhui = datetime.date.today()
    return aujourdhui.year if aujourdhui.month >= 8 else aujourdhui.year - 1


def Imprimer_calendrier_annuel(request):
    """ Génère le PDF A4 paysage du calendrier annuel """
    if not request.user.has_perm("core.calendrier_annuel"):
        return JsonResponse({"erreur": "Vous n'avez pas la permission d'accéder à cette fonctionnalité"}, status=401)
    type_annee = request.POST.get("type_annee")
    try:
        annee = int(request.POST.get("annee"))
    except (TypeError, ValueError):
        annee = None
    if type_annee not in ("scolaire", "civile") or not annee or not 1900 <= annee <= 2200:
        return JsonResponse({"erreur": "Veuillez sélectionner une année valide"}, status=401)
    impression = utils_impression_calendrier_annuel.Impression(annee=annee, type_annee=type_annee)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


class View(CustomView, TemplateView):
    template_name = "outils/calendrier_annuel.html"
    menu_code = "calendrier_annuel"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Calendrier annuel"
        context['box_titre'] = ""
        context['box_introduction'] = "Ce calendrier annuel vous permet notamment de vérifier si les périodes de vacances et les jours fériés ont bien été paramétrés."
        annee_scolaire = Get_annee_scolaire_courante()
        context['annees_impression'] = list(range(annee_scolaire - 2, annee_scolaire + 4))
        context['annee_scolaire_courante'] = annee_scolaire
        context['annee_civile_courante'] = datetime.date.today().year
        return context
