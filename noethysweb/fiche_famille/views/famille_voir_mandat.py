# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from django.http import JsonResponse
from fiche_famille.views.famille import Onglet


def Impression_pdf(request):
    # Récupération des données du formulaire
    idmandat = int(request.POST.get("idmandat"))
    idfamille = int(request.POST.get("idfamille"))

    # Création du PDF
    from fiche_famille.utils import utils_impression_mandat
    impression = utils_impression_mandat.Impression(titre="Edition des contacts", dict_donnees={"idmandat": idmandat, "idfamille": idfamille})
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier, "categorie": "mandat_sepa", "label_fichier": "Mandat", "champs": {}, "idfamille": idfamille})


class View(Onglet, TemplateView):
    template_name = "fiche_famille/famille_voir_mandat.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Aperçu d'un mandat"
        context['box_introduction'] = "Cliquez sur Aperçu PDF ou Envoyer par Email."
        context['onglet_actif'] = "mandats"
        return context
