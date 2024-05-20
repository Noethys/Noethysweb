# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import time, json
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.template.context_processors import csrf
from crispy_forms.utils import render_crispy_form
from core.utils import utils_parametres
from core.data import data_modeles_emails
from fiche_famille.views.famille import Onglet
from fiche_famille.forms.famille_releve_prestations import Formulaire, Formulaire_periode


def Get_form_periode(request):
    action = request.POST.get("action", None)
    index = request.POST.get("index", None)

    initial_data = {}
    if "valeur" in request.POST:
        initial_data = json.loads(request.POST["valeur"])
        initial_data["index"] = index

    # Création et rendu html du formulaire
    if action in ("ajouter", "modifier"):
        form = Formulaire_periode(request=request, initial=initial_data)
        return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})

    # Validation du formulaire
    form = Formulaire_periode(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["<b>%s</b> : %s " % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": messages_erreurs}, status=401)

    # Transformation en chaîne
    dict_retour = dict(form.cleaned_data)
    del dict_retour["index"]
    return JsonResponse({"valeur": dict_retour, "index": form.cleaned_data["index"]})


def Generer_pdf(request):
    time.sleep(1)

    # Récupération des options
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    parametres = form.cleaned_data
    parametres["periodes"] = json.loads(parametres["periodes"])
    if not parametres["periodes"]:
        return JsonResponse({"erreur": "Vous devez créer au moins une période"}, status=401)

    # Mémorisation des périodes
    if parametres["memoriser"]:
        utils_parametres.Set_categorie(categorie="releve_prestations", utilisateur=request.user, parametres=dict(parametres))

    # Intégration du IDfamille
    parametres["idfamille"] = int(request.POST["idfamille"])

    # Création du PDF
    from fiche_famille.utils import utils_impression_releve_prestations
    impression = utils_impression_releve_prestations.Impression(titre="Relevé des prestations", dict_donnees=parametres)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()

    # Récupération des valeurs de fusion
    champs = {motcle: impression.Get_champs_fusion().get(motcle, "") for motcle, label in data_modeles_emails.Get_mots_cles("releve_prestations")}
    return JsonResponse({"nom_fichier": nom_fichier, "categorie": "releve_prestations", "label_fichier": "Relevé des prestations", "champs": champs, "idfamille": parametres["idfamille"]})


class View(Onglet, TemplateView):
    template_name = "fiche_famille/famille_releve_prestations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Edition d'un relevé des prestations"
        context['box_introduction'] = "Le relevé des prestations permet d'afficher dans un unique document une liste de prestations ou de factures selon les critères souhaités. Commencez par créer des périodes de prestations ou de factures, puis cliquez sur le bouton Générer le PDF ou Envoyer par Email."
        context['onglet_actif'] = "outils"
        context['form'] = Formulaire(request=self.request, idfamille=kwargs["idfamille"])
        context['idfamille'] = kwargs["idfamille"]
        return context
