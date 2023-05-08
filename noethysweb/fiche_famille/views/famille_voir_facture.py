# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.models import MessageFacture, ModeleImpression
from core.data import data_modeles_emails
from facturation.forms.factures_options_impression import Formulaire as Form_parametres
from facturation.forms.factures_choix_modele import Formulaire as Form_modele_document
from facturation.forms.choix_modele_impression import Formulaire as Form_modele_impression
from fiche_famille.views.famille import Onglet


def Impression_pdf(request):
    # Récupération des données du formulaire
    valeurs_form_modele_impression = json.loads(request.POST.get("form_modele_impression"))
    valeurs_form_modele_document = json.loads(request.POST.get("form_modele_document"))
    valeurs_form_parametres = json.loads(request.POST.get("form_parametres"))
    idfacture = int(request.POST.get("idfacture"))
    idfamille = int(request.POST.get("idfamille"))

    # Récupération du modèle d'impression
    IDmodele_impression = int(valeurs_form_modele_impression.get("modele_impression", 0))

    if IDmodele_impression:
        modele_impression = ModeleImpression.objects.get(pk=IDmodele_impression)
        dict_options = json.loads(modele_impression.options)
        dict_options["modele"] = modele_impression.modele_document
    else:
        # Récupération du modèle de document
        form_modele_document = Form_modele_document(valeurs_form_modele_document)
        if not form_modele_document.is_valid():
            return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document"}, status=401)

        # Récupération des options d'impression
        form_parametres = Form_parametres(valeurs_form_parametres, request=request)
        if not form_parametres.is_valid():
            return JsonResponse({"erreur": "Veuillez compléter les options d'impression"}, status=401)

        dict_options = form_parametres.cleaned_data
        dict_options.update(form_modele_document.cleaned_data)

    # Création du PDF
    from facturation.utils import utils_facturation
    facturation = utils_facturation.Facturation()
    resultat = facturation.Impression(liste_factures=[idfacture,], dict_options=dict_options)

    # Récupération des valeurs de fusion
    champs = {motcle: resultat["champs"][idfacture].get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("facture")}
    return JsonResponse({"nom_fichier": resultat["nom_fichier"], "categorie": "facture", "label_fichier": "Facture", "champs": champs, "idfamille": idfamille})


class View(Onglet, TemplateView):
    template_name = "fiche_famille/famille_voir_facture.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Aperçu d'une facture"
        context['box_introduction'] = "Ajustez si besoin les options d'impression et cliquez sur Aperçu PDF ou Envoyer par Email."
        context['onglet_actif'] = "factures"
        context['form_modele_impression'] = Form_modele_impression(categorie="facture")
        context['form_modele_document'] = Form_modele_document()
        context['form_parametres'] = Form_parametres(request=self.request)
        context["messages"] = MessageFacture.objects.all().order_by("titre")
        return context
