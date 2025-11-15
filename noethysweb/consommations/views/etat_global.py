# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, time
from django.views.generic import TemplateView
from django.http import JsonResponse, QueryDict
from django.shortcuts import render
from django.db.models import Q
from django.template import loader
from django.utils.safestring import mark_safe
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Unite, Parametre
from consommations.forms.etat_global import Form_selection_periode, Form_selection_options, Form_selection_activites, Form_profil_configuration


def get_data_profil(donnees=None, request=None):
    """ Récupère les données à sauvegarder dans le profil de configuration """
    dict_donnees = json.loads(donnees)

    # Conversion des données en querydict
    qdict = QueryDict("", mutable=True)
    for item in dict_donnees["options"]:
        qdict.appendlist(item["name"], item["value"])
    qdict.mutable = False

    form = Form_selection_options(qdict, request=request)

    # Validation des paramètres
    if not form.is_valid():
        #todo : pas fonctionnel
        print("Erreurs =", form.errors.as_data())
        return JsonResponse({"erreur": "Les paramètres ne sont pas valides"}, status=401)

    return {"options": form.cleaned_data, "parametres": dict_donnees["parametres"]}


def Appliquer_parametres(request):
    # Récupération de la période
    form = Form_selection_periode(json.loads(request.POST.get("form_selection_periode")))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez renseigner la période"}, status=401)
    periode = form.cleaned_data.get("periode")

    # Récupération des activités
    form = Form_selection_activites(json.loads(request.POST.get("form_selection_activites")))
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez sélectionner des activités"}, status=401)
    activites = json.loads(form.cleaned_data.get("activites"))
    if not activites["ids"]:
        return JsonResponse({"erreur": "Veuillez sélectionner des activités"}, status=401)

    dict_unites = Get_unites(activites=activites, periode=periode)
    return render(request, "consommations/etat_global_parametres.html", context={"dict_unites": dict_unites, "periode": periode})


def Get_unites(activites=None, periode=None):
    date_debut, date_fin = utils_dates.ConvertDateRangePicker(periode)

    # Recherche des unités ouvertes
    if activites["type"] == "groupes_activites": condition_activites = Q(activite__groupes_activites__in=activites["ids"])
    if activites["type"] == "activites": condition_activites = Q(activite__in=activites["ids"])
    condition_periode = Q(activite__date_debut__lte=date_fin) & (Q(activite__date_fin__gte=date_debut) | Q(activite__date_fin__isnull=True))
    unites = Unite.objects.select_related('activite').filter(condition_activites, condition_periode).order_by("activite__date_debut", "activite_id", "ordre")

    # Regroupement par activité
    dict_unites = {}
    for unite in unites:
        dict_unites.setdefault(unite.activite, [])
        dict_unites[unite.activite].append(unite)

    return dict_unites


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
    date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres.get("periode"))
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

        # Application du profil de configuration
        if self.request.POST.get("params_profil"):
            profil = Parametre.objects.filter(idparametre=int(json.loads(self.request.POST.get("params_profil"))["profil"])).first()
            initial_data_options = json.loads(profil.parametre)["options"]
            initial_data_parametres = json.loads(profil.parametre)["parametres"]
            context["dict_parametres"] = json.dumps(initial_data_parametres)

        # Intégration des formulaires
        context["form_selection_options"] = Form_selection_options(initial=initial_data_options if "params_profil" in self.request.POST else None, request=self.request)
        context["form_selection_profil"] = Form_profil_configuration(data=json.loads(self.request.POST.get("params_profil")) if "params_profil" in self.request.POST else None, request=self.request)
        context["form_selection_periode"] = Form_selection_periode(data=json.loads(self.request.POST.get("params_periode")) if "params_periode" in self.request.POST else None, request=self.request)
        context["form_selection_activites"] = Form_selection_activites(data=json.loads(self.request.POST.get("params_activites")) if "params_activites" in self.request.POST else None, request=self.request)

        # Envoie le tableau des paramètres
        if context["form_selection_periode"].is_valid() and context["form_selection_activites"].is_valid() and self.request.POST.get("params_profil"):
            periode = context["form_selection_periode"].cleaned_data.get("periode")
            activites = json.loads(context["form_selection_activites"].cleaned_data.get("activites"))
            dict_unites = Get_unites(activites=activites, periode=periode)
            context["html_parametres"] = mark_safe(loader.render_to_string("consommations/etat_global_parametres.html",
                                                                           context={"dict_unites": dict_unites, "periode": periode}))
        return context

    def post(self, request, **kwargs):
        return self.render_to_response(self.get_context_data())
