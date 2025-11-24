# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Count
from core.models import Consommation, Activite
from core.views.base import CustomView
from core.utils import utils_parametres
from consommations.forms.suivi_pointage import Formulaire as Form_parametres_suivi_pointage


def Get_form_parametres(request):
    """ Renvoie le form des paramètres """
    parametres = utils_parametres.Get_categorie(categorie="suivi_pointage", utilisateur=request.user, parametres={"periode": "14", "activites": "{}", "afficher_jour": True})
    context = {"form_parametres_suivi_pointage": Form_parametres_suivi_pointage(request=request, initial=parametres)}
    return render(request, "consommations/suivi_pointage_parametres.html", context)


def Valider_form_parametres(request):
    """ Validation du form paramètres """
    form = Form_parametres_suivi_pointage(request.POST)
    if not form.is_valid():
        return JsonResponse({"erreur": "Il y a une erreur dans les paramètres"}, status=401)
    utils_parametres.Set_categorie(categorie="suivi_pointage", utilisateur=request.user, parametres=form.cleaned_data)
    return JsonResponse({"resultat": True})


def Get_pointage(request):
    """ Importation des consommations non pointées pour le widget """
    parametres = utils_parametres.Get_categorie(categorie="suivi_pointage", utilisateur=request.user, parametres={"periode": "14", "activites": "{}", "afficher_jour": True})

    # Activités
    try:
        param_activites = json.loads(parametres["activites"])
    except:
        param_activites = {}
    if param_activites.get("type") == "groupes_activites":
        liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
    elif param_activites.get("type") == "activites":
        liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])
    else:
        liste_activites = None

    # Période
    date_min = datetime.date.today() - datetime.timedelta(days=int(parametres["periode"]))
    date_max = datetime.date.today() - datetime.timedelta(days=0 if parametres["afficher_jour"] else 1)

    # Récupération des stats
    dict_pointage = {}
    if liste_activites:
        liste_pointage = Consommation.objects.select_related("activite").values("date", "activite__nom", "activite__pk").filter(date__gte=date_min, date__lte=date_max, etat="reservation", activite__in=liste_activites).annotate(nbre=Count("pk")).order_by("date", "activite__nom")
        for item in liste_pointage:
            dict_pointage.setdefault(item["date"], {"nbre_total": 0, "activites": []})
            dict_pointage[item["date"]]["activites"].append({"activite__nom": item["activite__nom"], "activite__pk": item["activite__pk"], "nbre": item["nbre"]})
            dict_pointage[item["date"]]["nbre_total"] += item["nbre"]
    return dict_pointage


class View(CustomView, TemplateView):
    menu_code = "suivi_pointage"
    template_name = "consommations/suivi_pointage_view.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Suivi du pointage"
        context["dict_pointage"] = Get_pointage(self.request)
        return context
