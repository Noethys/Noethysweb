# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from colorhash import ColorHash
from django.db.models import Q
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.views.generic import TemplateView
from django.core.cache import cache
from crispy_forms.utils import render_crispy_form
from core.models import Produit, Location
from core.views.base import CustomView
from core.utils import utils_parametres
from locations.forms.planning_locations_parametres import Formulaire as Formulaire_parametres
from locations.forms.supprimer_occurences import Formulaire as Form_supprimer_occurences
from fiche_famille.forms.famille_locations import Formulaire, FORMSET_PRESTATIONS
from fiche_famille.views.famille_locations import Form_valid_ajouter, Form_valid_modifier, Supprime_occurences


def Get_parametres(request):
    parametres_defaut = {
        "barre_afficher_heure": True,
        "barre_label": "famille+produit",
        "barre_label_observations": True,
        "barre_couleur": "famille",
        "heure_min": "00:00:00",
        "heure_max": "24:00:00",
        "vue_favorite": "resourceTimelineDay",
        "graduations_duree": "01:00:00",
        "graduations_largeur": "40",
    }
    key_cache = "planning_locations_parametres_user%d" % request.user.pk
    parametres = cache.get(key_cache, None)
    if not parametres:
        parametres = json.loads(utils_parametres.Get(utilisateur=request.user, nom="parametres", categorie="planning_locations", valeur=json.dumps(parametres_defaut)))
    for key, valeur in parametres_defaut.items():
        if key not in parametres:
            parametres[key] = valeur
    cache.set(key_cache, parametres, timeout=36000)
    return parametres


def Get_form_parametres(request):
    # Création et rendu html du formulaire
    form = Formulaire_parametres(request=request, initial=Get_parametres(request))
    return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})


def Valid_form_parametres(request):
    form = Formulaire_parametres(request.POST, request=request)
    if not form.is_valid():
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)

    utils_parametres.Set(nom="parametres", categorie="planning_locations", utilisateur=request.user, valeur=json.dumps(form.cleaned_data))
    cache.delete("planning_locations_parametres_user%d" % request.user.pk)
    return JsonResponse({"succes": True})


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

    # Récupération des paramètres
    parametres = Get_parametres(request)

    # Importation des locations
    conditions = Q(date_debut__lte=date_fin) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut))
    locations = Location.objects.select_related("famille", "produit").filter(conditions)
    resultats = []
    for location in locations:
        # Label de la barre
        if parametres["barre_label"] == "famille+produit": label = "%s - %s" % (location.famille.nom, location.produit.nom)
        elif parametres["barre_label"] == "produit+famille": label = "%s - %s" % (location.produit.nom, location.famille.nom)
        else: label = location.famille.nom
        if parametres["barre_label_observations"] and location.observations:
            label += " - %s" % location.observations

        # Couleur de la barre
        if parametres["barre_couleur"] == "famille": couleur = ColorHash(str(location.famille.pk)).hex
        if parametres["barre_couleur"] == "produit": couleur = location.produit.couleur

        # Description pour tooltip
        description = [
            "Début : %s" % datetime.datetime.strftime(location.date_debut, "%d/%m/%Y %H:%M"),
            "Fin : %s" % (datetime.datetime.strftime(location.date_fin, "%d/%m/%Y %H:%M") if location.date_fin else "Illimité"),
            "Observations : %s" % (location.observations or "-"),
            "Quantité : %d" % (location.quantite or 1),
        ]
        resultats.append({
            "id": str(location.pk),
            "title": label,
            "resourceId": str(location.produit_id),
            "start": str(location.date_debut),
            "end": str(location.date_fin or datetime.datetime(2999, 1, 1, 0, 0)),
            "color": couleur,
            "allDay": False,
            "overlap": False if location.quantite in (1, None) else True,
            "tooltip_titre": "%s</br>%s" % (location.famille.nom, location.produit.nom),
            "tooltip_description": "</br>".join(description),
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
    location = Location.objects.get(pk=int(request.POST["idlocation"]))
    if location.serie:
        form = Form_supprimer_occurences(request=request, mode="planning_locations", idlocation=location.pk)
        return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})
    else:
        location.delete()
        return JsonResponse({"succes": True})


def Supprimer_occurences(request):
    # Récupération des paramètres du formulaire de suppression
    idlocation = int(request.POST["idlocation"])
    form = Form_supprimer_occurences(request.POST, request=request, mode="planning_locations")
    if not form.is_valid():
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in form.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)

    # Supprime les occurences
    resultat = Supprime_occurences(idlocation=idlocation, donnees=form.cleaned_data["donnees"], periode=form.cleaned_data["periode"])
    if resultat != True:
        return JsonResponse({"erreur": resultat}, status=401)

    return JsonResponse({"succes": True})


class View(CustomView, TemplateView):
    menu_code = "planning_locations"
    template_name = "locations/planning_locations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Planning des locations"
        context["parametres"] = Get_parametres(self.request)
        return context
