# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Q
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Unite
from consommations.forms.etat_global import Form_selection_periode, Form_selection_activites, Form_selection_options, Form_profil_configuration


def Appliquer_parametres(request):
    # Récupération de la période
    form = Form_selection_periode(json.loads(request.POST.get("form_selection_periode")))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez renseigner la période"}, status=401)
    periode = form.cleaned_data.get("periode")
    date_debut = utils_dates.ConvertDateENGtoDate(periode.split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(periode.split(";")[1])

    # Récupération des activités
    form = Form_selection_activites(json.loads(request.POST.get("form_selection_activites")))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner des activités"}, status=401)
    activites = json.loads(form.cleaned_data.get("activites"))

    if not activites["ids"]:
        return JsonResponse({"erreur": "Veuillez sélectionner des activités"}, status=401)

    # Recherche des unités ouvertes
    if activites["type"] == "groupes_activites": condition_activites = Q(activite__groupes_activites__in=activites["ids"])
    if activites["type"] == "activites": condition_activites = Q(activite__in=activites["ids"])
    unites = Unite.objects.select_related('activite').filter(condition_activites, date_debut__lte=date_fin, date_fin__gte=date_debut).order_by("ordre")

    # Regroupement par activité
    dict_unites = {}
    for unite in unites:
        dict_unites.setdefault(unite.activite, [])
        dict_unites[unite.activite].append(unite)

    context = {
        "dict_unites": dict_unites,
        "periode": periode,
    }
    return render(request, 'consommations/etat_global_parametres.html', context)


def Generer_pdf(request):
    time.sleep(1)

    # Récupération des options
    form = Form_selection_options(request.POST)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner des activités"}, status=401)
    options = form.cleaned_data

    # Récupération des paramètres
    parametres = json.loads(request.POST.get('"liste_parametres'))
    if not parametres:
        return JsonResponse({"erreur": "Vous devez définir les paramètres"}, status=401)

    # Récupération de la période
    periode = parametres.get("periode")
    date_debut = utils_dates.ConvertDateENGtoDate(periode.split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(periode.split(";")[1])
    del parametres["periode"]

    dict_donnees = {
        "options": options,
        "parametres": parametres,
        "date_debut": date_debut,
        "date_fin": date_fin,
    }

    # Création du PDF
    from consommations.utils import utils_impression_etat_global
    impression = utils_impression_etat_global.Impression(titre="Etat global des consommations", dict_donnees=dict_donnees)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})


class View(CustomView, TemplateView):
    menu_code = "etat_global"
    template_name = "consommations/etat_global.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Etat global des consommations"
        context['form_selection_periode'] = Form_selection_periode(request=self.request)
        context['form_profil_configuration'] = Form_profil_configuration(request=self.request)
        context['form_selection_activites'] = Form_selection_activites(request=self.request)
        context['form_selection_options'] = Form_selection_options(request=self.request)
        return context

