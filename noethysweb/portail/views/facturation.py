# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.shortcuts import render
from portail.views.base import CustomView
from core.models import Facture, Prestation
from core.utils import utils_portail


def get_detail_facture(request):
    """ Génére un texte HTML contenant le détail d'une facture """
    idfacture = int(request.POST.get("idfacture", 0))

    # Importation de la facture
    facture = Facture.objects.get(pk=idfacture)
    if facture.famille != request.user.famille:
        return JsonResponse({"texte": "Accès interdit"}, status=401)

    # Importation des prestations
    prestations = Prestation.objects.select_related("individu", "activite").filter(facture=facture).order_by("date")

    # Création du texte HTML
    context = {
        "facture": facture,
        "prestations": prestations,
        "parametres_portail": utils_portail.Get_dict_parametres(),
    }
    return render(request, 'portail/detail_facture.html', context)



class View(CustomView, TemplateView):
    menu_code = "portail_facturation"
    template_name = "portail/facturation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Facturation"
        context['liste_factures'] = Facture.objects.filter(famille=self.request.user.famille).order_by("-date_edition")
        context['liste_factures_impayees'] = [facture.solde_actuel for facture in Facture.objects.filter(famille=self.request.user.famille, solde_actuel__gt=0)]
        return context
