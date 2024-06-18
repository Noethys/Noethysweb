# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import time
from django.http import JsonResponse
from django.views.generic import TemplateView
from fiche_famille.views.famille import Onglet
from individus.forms.edition_renseignements import Formulaire


def Generer_pdf(request):
    time.sleep(1)

    # Récupération des options
    form = Formulaire(request.POST, idfamille=int(request.POST.get("idfamille")), request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    options = form.cleaned_data
    if not options.get("rattachements", []):
        return JsonResponse({"erreur": "Vous devez sélectionner au moins un individu"}, status=401)

    # Création du PDF
    from individus.utils import utils_impression_renseignements
    impression = utils_impression_renseignements.Impression(titre="Renseignements", dict_donnees=options)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})


class View(Onglet, TemplateView):
    template_name = "fiche_famille/famille_edition_renseignements.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Edition des fiches de renseignements"
        context['box_introduction'] = "Sélectionnez les individus à inclure dans le document et cliquez sur le bouton Générer le PDF."
        context['onglet_actif'] = "outils"
        context['form'] = Formulaire(idfamille=kwargs["idfamille"], request=self.request)
        context['idfamille'] = kwargs["idfamille"]
        return context
