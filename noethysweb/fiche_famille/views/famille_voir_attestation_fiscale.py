# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.views.generic import TemplateView
from django.http import JsonResponse
from core.data import data_modeles_emails
from facturation.forms.attestations_fiscales_options_impression import Formulaire as Form_parametres
from facturation.forms.attestations_fiscales_choix_modele import Formulaire as Form_modele
from fiche_famille.views.famille import Onglet


def Impression_pdf(request):
    # Récupération des données du formulaire
    valeurs_form_modele = json.loads(request.POST.get("form_modele"))
    valeurs_form_parametres = json.loads(request.POST.get("form_parametres"))
    idattestation = int(request.POST.get("idattestation"))
    idfamille = int(request.POST.get("idfamille"))

    # Récupération du modèle de document
    form_modele = Form_modele(valeurs_form_modele)
    if not form_modele.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)

    # Récupération des options d'impression
    form_parametres = Form_parametres(valeurs_form_parametres, request=request)
    if not form_parametres.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les options d'impression"}, status=401)

    dict_options = form_parametres.cleaned_data
    dict_options.update(form_modele.cleaned_data)

    # Création du PDF
    from facturation.utils import utils_attestations_fiscales
    facturation = utils_attestations_fiscales.Facturation()
    resultat = facturation.Impression(liste_attestations_fiscales=[idattestation], dict_options=dict_options)

    # Récupération des valeurs de fusion
    champs = {motcle: resultat["champs"][idattestation].get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("attestation_fiscale")}
    return JsonResponse({"nom_fichier": resultat["nom_fichier"], "categorie": "attestation_fiscale", "label_fichier": "Attestation fiscale", "champs": champs, "idfamille": idfamille})


class View(Onglet, TemplateView):
    template_name = "fiche_famille/famille_voir_attestation_fiscale.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Aperçu d'une attestation fiscale"
        context['box_introduction'] = "Ajustez si besoin les options d'impression et cliquez sur Aperçu PDF ou Envoyer par Email."
        context['onglet_actif'] = "outils"
        context['form_modele'] = Form_modele()
        context['form_parametres'] = Form_parametres(request=self.request)
        return context
