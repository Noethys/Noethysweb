# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from django.views.generic import TemplateView
from cotisations.forms.cotisations_choix_modele import Formulaire as Form_modele
from fiche_famille.views.famille import Onglet
import json
from django.http import JsonResponse
from core.data import data_modeles_emails


def Impression_pdf(request):
    # Récupération des données du formulaire
    valeurs_form_modele = json.loads(request.POST.get("form_modele"))
    idcotisation = int(request.POST.get("idcotisation"))
    idfamille = int(request.POST.get("idfamille"))

    # Récupération du modèle de document
    form_modele = Form_modele(valeurs_form_modele)
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)
    dict_options = form_modele.cleaned_data

    # Création du PDF
    from cotisations.utils import utils_cotisations
    cotisations = utils_cotisations.Cotisations()
    resultat = cotisations.Impression(liste_cotisations=[idcotisation,], dict_options=dict_options)

    # Récupération des valeurs de fusion
    champs = {motcle: resultat["champs"][idcotisation].get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("cotisation")}
    return JsonResponse({"nom_fichier": resultat["nom_fichier"], "categorie": "cotisation", "label_fichier": "Adhésion", "champs": champs, "idfamille": idfamille})



class View(Onglet, TemplateView):
    template_name = "fiche_famille/famille_voir_cotisation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Aperçu d'une adhésion"
        context['box_introduction'] = "Sélectionnez un modèle de document et cliquez sur Aperçu PDF ou Envoyer par Email."
        context['onglet_actif'] = "cotisations"
        context['form_modele'] = Form_modele()
        return context

