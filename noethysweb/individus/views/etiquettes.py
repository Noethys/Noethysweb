# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.shortcuts import redirect
from django.http import JsonResponse
from core.views import crud
from individus.forms.etiquettes import Formulaire_categorie, Formulaire_parametres


def Impression_pdf(request):
    # Récupération des données du formulaire
    valeurs_form = json.loads(request.POST.get("form_general"))

    # Catégorie
    form_categorie = Formulaire_categorie(valeurs_form)
    form_categorie.is_valid()
    categorie = form_categorie.cleaned_data["categorie"]

    # Paramètres
    form_parametres = Formulaire_parametres(valeurs_form, categorie=categorie, request=request)
    if not form_parametres.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres"}, status=401)
    if not form_parametres.cleaned_data["modele"]:
        return JsonResponse({"erreur": "Veuillez sélectionner un modèle de document dans la liste proposée"}, status=401)

    # Coches
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins une ligne dans la liste"}, status=401)

    # Mix des valeurs des forms
    dict_options = form_parametres.cleaned_data
    dict_options["categorie"] = categorie
    dict_options["coches"] = coches

    # Création du PDF
    from individus.utils import utils_impression_etiquettes
    return utils_impression_etiquettes.Impression(dict_options=dict_options)


class Page(crud.Page):
    menu_code = "etiquettes_individus"
    template_name = "individus/etiquettes.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Edition d'étiquettes et de badges"
        context["categorie"] = "famille" if "etiquettes_familles" in str(context["view"]) else "individu"
        context['form_categorie'] = Formulaire_categorie(categorie=context["categorie"])
        context['form_parametres'] = Formulaire_parametres(categorie=context["categorie"], request=self.request)
        return context

    def post(self, request, **kwargs):
        """ Redirige vers la page Liste_individus ou Liste_familles """
        form_categorie = Formulaire_categorie(request.POST)
        form_categorie.is_valid()
        return redirect("etiquettes_%ss" % form_categorie.cleaned_data["categorie"])
