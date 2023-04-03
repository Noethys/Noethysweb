# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.views.generic import TemplateView
from django.db.models import Sum, Q, F, DurationField, ExpressionWrapper
from crispy_forms.utils import render_crispy_form
from core.models import EvenementCollaborateur, Collaborateur
from core.views.base import CustomView
from core.utils import utils_dates
from collaborateurs.forms.collaborateur_evenements import Formulaire
from collaborateurs.views.collaborateur_evenements import Form_valid_ajouter, Form_valid_modifier
from collaborateurs.forms.appliquer_modele_planning import Formulaire as Formulaire_appliquer_modele
from collaborateurs.views.appliquer_modele_planning import Form_valid_appliquer_modele


def Get_collaborateurs(request):
    # Récupération de la période affichée
    date_debut = datetime.datetime.strptime(request.POST["date_debut"], "%Y-%m-%d %H:%M").date()
    date_fin = datetime.datetime.strptime(request.POST["date_fin"], "%Y-%m-%d %H:%M").date()

    resultats = []
    conditions = Q(contratcollaborateur__date_debut__lte=date_fin) & (Q(contratcollaborateur__date_fin__isnull=True) | Q(contratcollaborateur__date_fin__gte=date_debut))
    conditions &= (Q(groupes__superviseurs=request.user) | Q(groupes__superviseurs__isnull=True))
    collaborateurs = Collaborateur.objects.filter(conditions).order_by("nom", "prenom").annotate(
            duree=Sum(ExpressionWrapper(F("evenementcollaborateur__date_fin") - F("evenementcollaborateur__date_debut"), output_field=DurationField()),
                      filter=Q(evenementcollaborateur__date_fin__gte=date_debut, evenementcollaborateur__date_debut__lte=date_fin))
        )
    for collaborateur in collaborateurs:
        resultats.append({
            "id": str(collaborateur.pk),
            "title": collaborateur.Get_nom(),
            "nom_collaborateur": collaborateur.Get_nom(),
            "duree": utils_dates.DeltaEnStr(collaborateur.duree),
        })
    return JsonResponse({"collaborateurs": resultats})


def Get_evenements(request):
    # Récupération de la période affichée
    date_debut = datetime.datetime.strptime(request.POST["date_debut"], "%Y-%m-%d %H:%M").date()
    date_fin = datetime.datetime.strptime(request.POST["date_fin"], "%Y-%m-%d %H:%M").date()

    # Importation des évènements
    conditions = (Q(collaborateur__groupes__superviseurs=request.user) | Q(collaborateur__groupes__superviseurs__isnull=True))
    evenements = EvenementCollaborateur.objects.select_related("collaborateur", "type_evenement").filter(conditions, date_debut__lte=date_fin, date_fin__gte=date_debut)
    resultats = []
    for evenement in evenements:
        resultats.append({
            "id": str(evenement.pk),
            "title": evenement.titre or evenement.type_evenement.nom,
            "resourceId": str(evenement.collaborateur_id),
            "start": str(evenement.date_debut),
            "end": str(evenement.date_fin),
            "color": evenement.type_evenement.couleur,
            "allDay": False,
        })

    return JsonResponse({"evenements": resultats})


def Get_form_appliquer_modele(request):
    """ Retourne un form pour appliquer modèle """
    form = Formulaire_appliquer_modele(request=request)
    return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})


def Valid_form_appliquer_modele(request):
    # Validation du form
    retour = Form_valid_appliquer_modele(request=request)

    # Retour de la réponse
    if retour["resultat"]:
        return JsonResponse({"succes": True, "messages": retour["messages"]})
    else:
        return JsonResponse({"succes": False, "messages": retour["messages"]}, status=401)


def Get_form_detail_evenement(request):
    # Importation de l'évènement si c'est une modification
    idevenement = int(request.POST.get("idevenement", 0) or 0)
    evenement = EvenementCollaborateur.objects.get(pk=idevenement) if idevenement else None

    # Importation des valeurs par défaut si c'est un ajout
    data_event = json.loads(request.POST.get("data_event", "{}"))
    data_initial = {}
    if data_event:
        data_initial = {
            "collaborateur": int(data_event["collaborateur"]),
            "date_debut": datetime.datetime.strptime(data_event["date_debut"], "%Y-%m-%d %H:%M"),
            "date_fin": datetime.datetime.strptime(data_event["date_fin"], "%Y-%m-%d %H:%M"),
        }

    # Création du contexte
    context = {}
    context.update(csrf(request))

    # Formateg du form en html
    form_detail = Formulaire(instance=evenement, request=request, initial=data_initial)
    form_html = render_crispy_form(form_detail, context=context)
    return JsonResponse({"form_html": form_html})


def Valid_form_detail_evenement(request):
    # Importation de l'évènement si c'est une modification
    evenement = EvenementCollaborateur.objects.get(pk=int(request.POST["idevenement"])) if request.POST["idevenement"] != "None" else None
    form = Formulaire(request.POST, request=request, instance=evenement)

    # Validation du form
    if evenement:
        resultat = Form_valid_modifier(form=form, request=request, object=form.instance)
    else:
        resultat = Form_valid_ajouter(form=form, request=request, object=form.instance)

    # Retour de la réponse
    if resultat == True or isinstance(resultat, EvenementCollaborateur):
        return JsonResponse({"succes": True})
    else:
        liste_erreurs = ", ".join([erreur[0].message for field, erreur in resultat.errors.as_data().items()])
        return JsonResponse({"erreur": liste_erreurs}, status=401)


def Modifier_evenement(request):
    data_event = json.loads(request.POST.get("data_event", "{}"))
    evenement = EvenementCollaborateur.objects.get(pk=int(data_event["idevenement"]))
    if data_event.get("collaborateur", None):
        evenement.collaborateur_id = int(data_event["collaborateur"])
    evenement.date_debut = datetime.datetime.strptime(data_event["date_debut"], "%Y-%m-%d %H:%M")
    evenement.date_fin = datetime.datetime.strptime(data_event["date_fin"], "%Y-%m-%d %H:%M")
    evenement.save()
    return JsonResponse({"succes": True})


def Supprimer_evenement(request):
    EvenementCollaborateur.objects.get(pk=int(request.POST["idevenement"])).delete()
    return JsonResponse({"succes": True})


class View(CustomView, TemplateView):
    menu_code = "planning_collaborateurs"
    template_name = "collaborateurs/planning_collaborateurs.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Planning des évènements"
        return context
