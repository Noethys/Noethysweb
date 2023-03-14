# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.views.generic import TemplateView
from django.http import JsonResponse
from core.data import data_modeles_emails
from fiche_famille.views.famille import Onglet
from locations.forms.locations_choix_modele import Formulaire as Form_modele


def Impression_pdf(request):
    # Récupération des données du formulaire
    valeurs_form_modele = json.loads(request.POST.get("form_modele"))
    idlocation = int(request.POST.get("idlocation"))
    idfamille = int(request.POST.get("idfamille"))

    # Récupération du modèle de document
    form_modele = Form_modele(valeurs_form_modele)
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)
    dict_options = form_modele.cleaned_data

    # Création du PDF
    from locations.utils import utils_locations
    locations = utils_locations.Locations()
    resultat = locations.Impression(liste_locations=[idlocation,], dict_options=dict_options)

    # Récupération des valeurs de fusion
    champs = {motcle: resultat["champs"][idlocation].get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("location")}
    return JsonResponse({"nom_fichier": resultat["nom_fichier"], "categorie": "location", "label_fichier": "Location", "champs": champs, "idfamille": idfamille})


class View(Onglet, TemplateView):
    template_name = "fiche_famille/famille_voir_location.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Aperçu d'une location"
        context['box_introduction'] = "Sélectionnez un modèle de document et cliquez sur Aperçu PDF ou Envoyer par Email."
        context['onglet_actif'] = "locations"
        context['form_modele'] = Form_modele()
        return context
