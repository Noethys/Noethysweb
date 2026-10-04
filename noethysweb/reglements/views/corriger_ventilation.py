# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from decimal import Decimal
from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.models import Famille
from core.views.base import CustomView
from core.utils import utils_preferences
from reglements.utils import utils_ventilation


def Format_montant(montant=Decimal(0)):
    """ Formate un montant comme le filtre de template 'montant' """
    return "%0.2f %s" % (montant, utils_preferences.Get_symbole_monnaie())


def Get_apercu(request):
    """ Simule la ventilation automatique d'une famille sans rien enregistrer """
    if not request.user.has_perm("core.corriger_ventilation"):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation d'accéder à cette fonctionnalité"}, status=401)
    try:
        idfamille = int(request.POST.get("idfamille"))
    except (TypeError, ValueError):
        return JsonResponse({"erreur": "Famille inconnue"}, status=400)

    resultat = utils_ventilation.Calculer_ventilation_auto(IDfamille=idfamille, enregistrer=False)

    # Regroupement des affectations par règlement et par prestation (dans l'ordre d'affectation)
    reglements, prestations = {}, {}
    for reglement, prestation, montant in resultat["affectations"]:
        reglements.setdefault(reglement.pk, {"objet": reglement, "montant": Decimal(0)})["montant"] += montant
        prestations.setdefault(prestation.pk, {"objet": prestation, "montant": Decimal(0)})["montant"] += montant

    anomalies = utils_ventilation.GetAnomaliesVentilation(idfamille=idfamille).get(idfamille, {})
    reste_du = max(anomalies.get("total_prestations", Decimal(0)) - anomalies.get("total_ventilations", Decimal(0)) - resultat["total"], Decimal(0))

    return JsonResponse({
        "possible": resultat["possible"],
        "reglements": [{
            "date": item["objet"].date.strftime("%d/%m/%Y"),
            "mode": item["objet"].mode.label,
            "numero": item["objet"].numero_piece or "",
            "montant": Format_montant(item["montant"]),
        } for item in reglements.values()],
        "prestations": [{
            "date": item["objet"].date.strftime("%d/%m/%Y"),
            "label": item["objet"].label,
            "activite": item["objet"].activite.nom if item["objet"].activite else "",
            "montant": Format_montant(item["montant"]),
        } for item in prestations.values()],
        "nbre_affectations": len(resultat["affectations"]),
        "total": Format_montant(resultat["total"]),
        "reste_du": Format_montant(reste_du) if reste_du > 0 else "",
    })


class View(CustomView, TemplateView):
    menu_code = "corriger_ventilation"
    template_name = "reglements/corriger_ventilation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Ventilation"
        context['box_titre'] = "Corriger la ventilation"
        context['box_introduction'] = "Une anomalie existe lorsqu'une partie des règlements d'une famille n'est pas affectée à ses prestations. " \
                                      "La ventilation automatique affecte le montant disponible de chaque règlement aux prestations restant dues, dans l'ordre de saisie."

        dict_anomalies = utils_ventilation.GetAnomaliesVentilation()
        familles_manuelles = utils_ventilation.Get_familles_ventilation_manuelle(liste_idfamilles=list(dict_anomalies.keys()))

        items = []
        for famille in Famille.objects.filter(pk__in=dict_anomalies.keys()).order_by("nom"):
            valeurs = dict_anomalies[famille.pk]
            taux = 0
            if valeurs["total_a_ventiler"]:
                taux = int(valeurs["total_ventilations"] * 100 / valeurs["total_a_ventiler"])
            items.append({"famille": famille, "valeurs": valeurs, "manuelle": famille.pk in familles_manuelles, "taux_ventile": max(0, min(taux, 100))})

        context['items'] = items
        if not items:
            context['box_introduction'] = ""
        context['nbre_anomalies'] = len(items)
        context['nbre_manuelles'] = len([item for item in items if item["manuelle"]])
        context['nbre_auto'] = context['nbre_anomalies'] - context['nbre_manuelles']
        context['total_a_ventiler'] = sum([item["valeurs"]["reste_a_ventiler"] for item in items], Decimal(0))
        context['symbole_monnaie'] = utils_preferences.Get_symbole_monnaie()
        context['heure_verification'] = datetime.datetime.now().strftime("%H:%M")
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        # Actualiser l'affichage
        if action == "actualiser":
            return render(request, self.template_name, self.get_context_data(**kwargs))

        # Récupère la liste des sélections
        try:
            liste_familles = [int(idfamille) for idfamille in json.loads(request.POST.get("selections"))]
        except Exception:
            liste_familles = []

        # Vérifie qu'au moins une ligne a été cochée
        if not liste_familles:
            messages.add_message(self.request, messages.ERROR, "Vous n'avez sélectionné aucune famille")
            return render(request, self.template_name, self.get_context_data(**kwargs))

        # Ventilation automatique
        resultat = {"nbre_familles": 0, "total": Decimal(0), "nbre_creations": 0, "idfamilles_manuelles": []}
        for idfamille in liste_familles:
            resultat_famille = utils_ventilation.Calculer_ventilation_auto(IDfamille=idfamille, enregistrer=True)
            if not resultat_famille["possible"]:
                resultat["idfamilles_manuelles"].append(idfamille)
            elif resultat_famille["affectations"]:
                resultat["nbre_familles"] += 1
                resultat["total"] += resultat_famille["total"]
                resultat["nbre_creations"] += resultat_famille["nbre_creations"]

        resultat["total_str"] = Format_montant(resultat["total"])
        resultat["familles_manuelles"] = Famille.objects.filter(pk__in=resultat["idfamilles_manuelles"]).order_by("nom")

        context = self.get_context_data(**kwargs)
        context["resultat"] = resultat
        return render(request, self.template_name, context)
