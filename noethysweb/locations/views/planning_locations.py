# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.views.generic import TemplateView
from crispy_forms.utils import render_crispy_form
from core.models import Produit, CategorieProduit, Location
from core.views.base import CustomView
from fiche_famille.forms.famille_locations import Formulaire, FORMSET_PRESTATIONS
from fiche_famille.views.famille_locations import Form_valid_ajouter, Form_valid_modifier


def Get_produits(request):
    resultats = []
    produits = Produit.objects.select_related("categorie").all().order_by("categorie__nom", "nom")
    for produit in produits:
        resultats.append({
            "id": str(produit.pk),
            "categorie": produit.categorie.nom,
            "title": produit.nom,
            "eventColor": produit.couleur,
        })
    return JsonResponse({"produits": resultats})


def Get_locations(request):
    # Récupération de la période affichée
    date_debut = datetime.datetime.strptime(request.POST["date_debut"], "%Y-%m-%d %H:%M").date()
    date_fin = datetime.datetime.strptime(request.POST["date_fin"], "%Y-%m-%d %H:%M").date()

    # Importation des locations
    locations = Location.objects.select_related("famille", "produit").filter(date_debut__lte=date_fin, date_fin__gte=date_debut)
    resultats = []
    for location in locations:
        resultats.append({
            "id": str(location.pk),
            "title": "%s - %s" % (location.produit.nom, location.famille.nom),
            "resourceId": str(location.produit_id),
            "start": str(location.date_debut),
            "end": str(location.date_fin),
            "eventColor": location.produit.couleur,
            "allDay": False,
        })

    return JsonResponse({"locations": resultats})


def Get_form_detail_location(request):
    # Importation de la location si c'est une modification
    idlocation = int(request.POST.get("idlocation", 0) or 0)
    location = Location.objects.get(pk=idlocation) if idlocation else None

    # Importation des valeurs par défaut si c'est un ajout
    data_event = json.loads(request.POST.get("data_event", "{}"))
    data_initial = {}
    if data_event:
        data_initial = {
            "produit": int(data_event["produit"]),
            "date_debut": datetime.datetime.strptime(data_event["date_debut"], "%Y-%m-%d %H:%M"),
            "date_fin": datetime.datetime.strptime(data_event["date_fin"], "%Y-%m-%d %H:%M"),
        }

    # Création du contexte
    context = {}
    context.update(csrf(request))

    # Intégration du formset dans le contexte
    form_detail_location = Formulaire(instance=location, request=request, initial=data_initial)
    context["formset_prestations"] = FORMSET_PRESTATIONS(instance=location)

    # Rendu du form en html
    form_html = render_crispy_form(form_detail_location, context=context)
    return JsonResponse({"form_html": form_html})


def Valid_form_detail_location(request):
    # Importation de la location si c'est une modification
    location = Location.objects.get(pk=int(request.POST["idlocation"])) if request.POST["idlocation"] != "None" else None
    form = Formulaire(request.POST, request=request, instance=location)

    # Validation du form
    if location:
        resultat = Form_valid_modifier(form=form, request=request, object=form.instance)
    else:
        resultat = Form_valid_ajouter(form=form, request=request, object=form.instance)

    # Retour de la réponse
    if resultat == True or isinstance(resultat, Location):
        return JsonResponse({"succes": True})
    else:
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in resultat.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)


def Modifier_location(request):
    data_event = json.loads(request.POST.get("data_event", "{}"))
    location = Location.objects.get(pk=int(data_event["idlocation"]))
    if data_event.get("produit", None):
        location.produit_id = int(data_event["produit"])
    location.date_debut = datetime.datetime.strptime(data_event["date_debut"], "%Y-%m-%d %H:%M")
    location.date_fin = datetime.datetime.strptime(data_event["date_fin"], "%Y-%m-%d %H:%M")
    location.save()
    return JsonResponse({"succes": True})


def Supprimer_location(request):
    Location.objects.get(pk=int(request.POST["idlocation"])).delete()
    return JsonResponse({"succes": True})


class View(CustomView, TemplateView):
    menu_code = "planning_locations"
    template_name = "locations/planning_locations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Planning des locations"
        return context
