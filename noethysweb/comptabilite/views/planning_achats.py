# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.views.generic import TemplateView
from crispy_forms.utils import render_crispy_form
from core.models import AchatDemande
from core.views.base import CustomView
from comptabilite.views.achats_demandes import Form_valid
from comptabilite.forms.achats_demandes import Formulaire


def Get_achats(request):
    # Récupération de la période affichée
    date_debut = datetime.datetime.strptime(request.POST["date_debut"], "%Y-%m-%d %H:%M").date()
    date_fin = datetime.datetime.strptime(request.POST["date_fin"], "%Y-%m-%d %H:%M").date()

    # Importation des achats
    demandes = AchatDemande.objects.select_related("collaborateur").filter(date_echeance__lte=date_fin, date_echeance__gte=date_debut)
    resultats = []
    for demande in demandes:
        if demande.etat == 0: couleur = "#dc3545"
        elif demande.etat == 100: couleur = "#28a745"
        else: couleur = "#ffc107"
        resultats.append({
            "id": str(demande.pk),
            "title": "%s - %s" % (demande.libelle, demande.collaborateur.Get_nom()),
            "start": str(demande.date_echeance),
            "end": str(demande.date_echeance),
            "color": couleur,
            "allDay": True,
            "overlap": True,
        })

    return JsonResponse({"demandes": resultats})


def Get_form_detail_achat(request):
    # Importation de la location si c'est une modification
    iddemande = int(request.POST.get("iddemande", 0) or 0)
    demande = AchatDemande.objects.get(pk=iddemande) if iddemande else None

    # Importation des valeurs par défaut si c'est un ajout
    data_event = json.loads(request.POST.get("data_event", "{}"))
    data_initial = {}
    if data_event:
        data_initial = {
            "date_echeance": datetime.datetime.strptime(data_event["date_echeance"], "%Y-%m-%d"),
        }

    # Création du contexte
    context = {}
    context.update(csrf(request))

    # Intégration du formset dans le contexte
    form_detail_achat = Formulaire(instance=demande, request=request, initial=data_initial, mode_affichage="planning")

    # Rendu du form en html
    form_html = render_crispy_form(form_detail_achat, context=context)
    return JsonResponse({"form_html": form_html})


def Valid_form_detail_achat(request):
    # Importation de la demande si c'est une modification
    demande = AchatDemande.objects.get(pk=int(request.POST["iddemande"])) if request.POST["iddemande"] != "None" else None
    form = Formulaire(request.POST, request=request, instance=demande)

    # Validation du form
    resultat = Form_valid(form=form, request=request, object=form.instance)

    # Retour de la réponse
    if resultat == True or isinstance(resultat, AchatDemande):
        return JsonResponse({"succes": True})
    else:
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in resultat.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)


def Modifier_achat(request):
    data_event = json.loads(request.POST.get("data_event", "{}"))
    demande = AchatDemande.objects.get(pk=int(data_event["iddemande"]))
    demande.date_echeance = datetime.datetime.strptime(data_event["date_echeance"], "%Y-%m-%d")
    demande.save()
    return JsonResponse({"succes": True})


def Supprimer_achat(request):
    AchatDemande.objects.get(pk=int(request.POST["iddemande"])).delete()
    return JsonResponse({"succes": True})


class View(CustomView, TemplateView):
    menu_code = "planning_achats"
    template_name = "comptabilite/planning_achats.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Planning des achats"
        return context
