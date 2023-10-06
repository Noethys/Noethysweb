# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Q
from django.shortcuts import render
from core.models import Activite, Historique
from core.views.base import CustomView
from core.utils import utils_parametres, utils_dates
from core.forms.selection_activites import Formulaire as Form_activites
from outils.forms.suivi_reservations_periode import Formulaire as Form_periode


def Get_form_activites(request):
    """ Renvoie une liste d'activités """
    activites = json.loads(request.POST.get("activites", None))
    context = {"form_activites": Form_activites(defaut=activites, request=request)}
    return render(request, "outils/suivi_reservations_activites.html", context)


def Get_form_periode(request):
    """ Renvoie le form choix de la période """
    periode_historique = request.POST.get("periode_historique", 12)
    periode_reservations = request.POST.get("periode_reservations", None)
    context = {"form_periode": Form_periode(request=request, initial={"periode_historique": periode_historique, "periode_reservations": periode_reservations})}
    return render(request, "outils/suivi_reservations_periode.html", context)


def Valider_form_activites(request):
    form = Form_activites(request.POST)
    if not form.is_valid():
        return JsonResponse({"erreur": "Il y a une erreur dans la sélection des activités"}, status=401)
    return JsonResponse({"activites": form.cleaned_data["activites"]})


def Valider_form_periode(request):
    form = Form_periode(request.POST)
    if not form.is_valid():
        return JsonResponse({"erreur": "Il y a une erreur dans la sélection de la période"}, status=401)
    return JsonResponse({"periode_historique": form.cleaned_data["periode_historique"], "periode_reservations": form.cleaned_data["periode_reservations"]})


def Get_parametres(request=None):
    """ Renvoie les paramètres d'affichage """
    parametres = utils_parametres.Get_categorie(categorie="suivi_reservations", utilisateur=request.user, parametres={
        "activites": {},
        "periode_historique": "12",
        "periode_reservations": None,
    })
    parametres["activites_reservations_json"] = json.dumps(parametres["activites"])
    parametres["periode_historique"] = parametres["periode_historique"]
    parametres["periode_reservations"] = parametres["periode_reservations"]
    return parametres


def Get_suivi_reservations(request):
    """ Renvoie le contenu de la table """
    parametres = json.loads(request.POST.get("parametres", None))

    # Si demande de modification des paramètres
    if parametres:
        utils_parametres.Set_categorie(categorie="suivi_reservations", utilisateur=request.user, parametres=parametres)

    # Importation des paramètres
    parametres = Get_parametres(request=request)
    context = {"data_suivi_reservations": Get_data(parametres=parametres, request=request)}
    context.update(parametres)
    return render(request, "outils/suivi_reservations_tableau.html", context)


def Get_data(parametres={}, request=None):
    """ Création des valeurs pour le suivi des réservations """
    # Importation des activités
    activites = parametres.get("activites", {"type": None, "ids": []})
    if "type" not in activites:
        return {}

    # vérifie que l'activité est bien accessible pour l'utilisateur
    conditions = Q()
    if request:
        conditions &= Q(structure__in=request.user.structures.all())
    if activites["type"] == "groupes_activites":
        conditions &= Q(groupes_activites__in=activites["ids"])
    if activites["type"] == "activites":
        conditions &= Q(pk__in=activites["ids"])
    liste_activites = Activite.objects.filter(conditions)

    # Recherche des actions dans l'historique
    periode_historique = parametres.get("periode_historique", 12)
    if parametres.get("affichage", None):
        periode_historique = parametres["affichage"]

    horodatage_min = datetime.datetime.now() - datetime.timedelta(hours=int(periode_historique))
    conditions = Q(classe="Consommation") & Q(horodatage__gte=horodatage_min) & Q(utilisateur__categorie="famille")
    conditions &= (Q(titre__icontains="Ajout") | Q(titre__icontains="Suppression")) & Q(activite__in=liste_activites)

    # Filtrage sur la période des réservations
    if parametres["periode_reservations"] and parametres["periode_reservations"] != "None":
        periode = utils_dates.ConvertDateRangePicker(parametres["periode_reservations"])
        conditions &= (Q(date__gte=periode[0]) & Q(date__lte=periode[1]))

    resultats = Historique.objects.select_related("famille", "individu").filter(conditions).order_by("-pk")
    return resultats


class View(CustomView, TemplateView):
    menu_code = "suivi_reservations"
    template_name = "outils/suivi_reservations_view.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Suivi des réservations"
        context['suivi_reservations_parametres'] = Get_parametres(request=self.request)
        return context
