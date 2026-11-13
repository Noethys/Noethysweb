# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.


import json, datetime
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_dates
from collaborateurs.forms.appliquer_modele_planning import Formulaire
from collaborateurs.utils import utils_evenements
from collaborateurs.utils.utils_modeles_planning import Generateur, Get_departs, Repartir, Memoriser_recents, Get_liste_modeles


def Get_liste(request):
    """ Liste des modèles pour le sélecteur, avec les collaborateurs concernés (AJAX) """
    try:
        collaborateurs = [int(valeur) for valeur in json.loads(request.POST.get("collaborateurs", "[]"))]
        date = datetime.date.fromisoformat(request.POST["date"]) if request.POST.get("date") else datetime.date.today()
    except (TypeError, ValueError):
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    return JsonResponse(Get_liste_modeles(utilisateur=request.user, collaborateurs=collaborateurs, date=date))


def Get_frise(request):
    """ Correspondance entre les semaines d'une période et les semaines du cycle des modèles (AJAX) """
    try:
        modeles = [int(valeur) for valeur in json.loads(request.POST.get("modeles", "[]"))]
        dates = sorted(set(datetime.date.fromisoformat(valeur) for valeur in json.loads(request.POST.get("dates", "[]"))))
    except (TypeError, ValueError):
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    if not modeles or not dates:
        return JsonResponse({"semaines": [], "modeles": [], "alertes": []})
    if (dates[-1] - dates[0]).days > 400:
        return JsonResponse({"erreur": "La période est trop longue pour afficher la correspondance des semaines"}, status=400)
    return JsonResponse(Generateur(modeles=modeles, dates=dates, departs=Get_departs(request)).Get_frise())


class View(CustomView, TemplateView):
    menu_code = "appliquer_modele_planning"
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Appliquer un modèle de planning"
        context['box_titre'] = "Appliquer un modèle de planning"
        context['box_introduction'] = "Sélectionnez une période d'application, les collaborateurs concernés, et le ou les modèles à appliquer."
        context['form'] = kwargs.get("form") or Formulaire(request=self.request)
        return context

    def post(self, request):
        retour = Form_valid_appliquer_modele(request=request)
        for type_message, message in retour["messages"]:
            messages.add_message(request, getattr(messages, type_message), message)
        if retour["resultat"]:
            return HttpResponseRedirect(reverse_lazy("collaborateurs_toc"))
        else:
            return self.render_to_response(self.get_context_data(form=retour["form"]))

def Form_valid_appliquer_modele(request=None):
    retour = {"resultat": False, "messages": [], "form": None}

    # Validation du formulaire
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        retour["form"] = form
        return retour

    # Récupération des valeurs du formulaire
    date_debut = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[1])
    modeles = form.cleaned_data["modeles"]
    collaborateurs = form.cleaned_data["collaborateurs"]
    dates = [date_debut + datetime.timedelta(days=n) for n in range((date_fin - date_debut).days + 1)]
    generateur = Generateur(modeles=modeles, dates=dates, departs=Get_departs(request))
    repartition, messages_restriction = Repartir(modeles=modeles, collaborateurs=collaborateurs, date=date_debut, forcer=request.POST.get("forcer_modeles") == "true")
    for message in messages_restriction:
        retour["messages"].append(("WARNING", message))

    # Génération des évènements
    for collaborateur in collaborateurs:
        modeles_autorises = {idmodele for idmodele, ids in repartition.items() if collaborateur.pk in ids}
        if not modeles_autorises:
            continue
        resultats = utils_evenements.Generation_evenements(idcollaborateur=collaborateur.pk, modeles=modeles, date_debut=date_debut, date_fin=date_fin, generateur=generateur,
                                                           modeles_autorises=modeles_autorises)

        if resultats["resultat"] == "erreur":
            retour["messages"].append(("ERROR", resultats["message_erreur"]))
            retour["form"] = form
            return retour

        if resultats["evenements_refus"]:
            retour["messages"].append(("ERROR", "%s : %d évènements n'ont pas été générés car ils sont en conflit avec d'autres évènements ou sont hors contrat" % (collaborateur.Get_nom(), len(resultats["evenements_refus"]))))
        if resultats["evenements_valides"]:
            retour["messages"].append(("SUCCESS", "%s : %d évènements ont été générés" % (collaborateur.Get_nom(), len(resultats["evenements_valides"]))))

    generateur.Memoriser_ancrages()
    Memoriser_recents(request.user, modeles)
    retour["resultat"] = True
    return retour
