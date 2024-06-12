# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from comptabilite.forms.edition_liste_achats import Formulaire


def Generer_pdf(request):
    # Récupération des options
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data

    # Création du PDF
    from comptabilite.utils import utils_impression_achats
    impression = utils_impression_achats.Impression(titre="Edition de la liste d'achats", dict_donnees=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    time.sleep(1)
    return JsonResponse({"nom_fichier": nom_fichier})


class View(CustomView, TemplateView):
    menu_code = "edition_liste_achats"
    template_name = "comptabilite/edition_liste_achats.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition d'une liste des achats"
        context['box_titre'] = "Edition d'une liste des achats"
        context['box_introduction'] = "Renseignez les paramètres et cliquez sur le bouton Générer le PDF. La génération du document peut nécessiter quelques instants d'attente."
        if "form" not in kwargs:
            context['form'] = Formulaire(request=self.request)
        return context
