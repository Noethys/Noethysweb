# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.http import JsonResponse, HttpResponseForbidden
from django.views.generic import TemplateView
from django.template.context_processors import csrf
from django.db import transaction
from django.db.models import Count, Max
from crispy_forms.utils import render_crispy_form
from core.views.base import CustomView
from core.models import AffectationCollaborateur, EvenementCollaborateur, LigneModelePlanningCollaborateur
from core.utils import utils_historique
from collaborateurs.utils.utils_affectations import Arbre
from parametrage.forms.affectations_collaborateurs import Formulaire

PERMISSION = "core.affectations_collaborateurs_liste"


def Verifie_permission(function):
    def _function(request, *args, **kwargs):
        if not request.user.has_perm(PERMISSION):
            return HttpResponseForbidden()
        return function(request, *args, **kwargs)
    return _function


def Get_donnees_arbre():
    nbre_evenements = dict(EvenementCollaborateur.objects.filter(affectation__isnull=False).values_list("affectation").annotate(nbre=Count("pk")))
    return Arbre().Get_liste_dict(nbre_evenements=nbre_evenements)


@Verifie_permission
def Get_arbre(request):
    return JsonResponse({"affectations": Get_donnees_arbre()})


@Verifie_permission
def Get_form(request):
    idaffectation = int(request.POST.get("idaffectation") or 0)
    instance = AffectationCollaborateur.objects.filter(pk=idaffectation).first() if idaffectation else None
    initial = {}
    if not instance and request.POST.get("idparent"):
        initial["parent"] = int(request.POST["idparent"])
    form = Formulaire(instance=instance, request=request, initial=initial)
    return JsonResponse({"form_html": render_crispy_form(form, context=csrf(request))})


@Verifie_permission
def Valid_form(request):
    idaffectation = int(request.POST.get("idaffectation") or 0)
    instance = AffectationCollaborateur.objects.filter(pk=idaffectation).first() if idaffectation else None
    ancien_parent = instance.parent_id if instance else None
    form = Formulaire(request.POST, instance=instance, request=request)
    if not form.is_valid():
        erreurs = [message for messages in form.errors.values() for message in messages]
        return JsonResponse({"erreur": " ".join(erreurs)}, status=401)

    affectation = form.save(commit=False)
    if not instance:
        # Nouvelle affectation : placée en dernier parmi ses soeurs
        ordre_max = AffectationCollaborateur.objects.filter(parent=affectation.parent).aggregate(Max("ordre"))["ordre__max"]
        affectation.ordre = (ordre_max or 0) + 1
    elif affectation.parent_id != ancien_parent:
        ordre_max = AffectationCollaborateur.objects.filter(parent=affectation.parent).exclude(pk=affectation.pk).aggregate(Max("ordre"))["ordre__max"]
        affectation.ordre = (ordre_max or 0) + 1
    affectation.save()
    form.save_m2m()

    utils_historique.Ajouter(titre="%s d'une affectation" % ("Modification" if instance else "Ajout"), detail=Arbre().Get_chemin(affectation.pk),
                             utilisateur=request.user, objet="Affectation", idobjet=affectation.pk, classe="AffectationCollaborateur")
    return JsonResponse({"succes": True, "idaffectation": affectation.pk, "affectations": Get_donnees_arbre()})


@Verifie_permission
def Deplacer(request):
    """ Déplace une affectation : nouveau parent et nouvelle position parmi ses soeurs """
    idaffectation = int(request.POST["idaffectation"])
    idparent = int(request.POST.get("idparent") or 0) or None
    position = int(request.POST.get("position", 0))

    arbre = Arbre()
    if idaffectation not in arbre.affectations:
        return JsonResponse({"erreur": "Cette affectation n'existe plus"}, status=401)
    if idparent and idparent in [idaffectation] + arbre.Get_descendants(idaffectation):
        return JsonResponse({"erreur": "Une affectation ne peut pas être placée sous l'une de ses sous-affectations"}, status=401)

    with transaction.atomic():
        soeurs = [affectation for affectation in arbre.enfants.get(idparent, []) if affectation.pk != idaffectation]
        affectation = arbre.affectations[idaffectation]
        soeurs.insert(max(0, min(position, len(soeurs))), affectation)
        for index, item in enumerate(soeurs, 1):
            modifie = item.ordre != index or (item.pk == idaffectation and item.parent_id != idparent)
            item.ordre = index
            if item.pk == idaffectation:
                item.parent_id = idparent
            if modifie:
                item.save(update_fields=["ordre", "parent"])

    return JsonResponse({"succes": True, "affectations": Get_donnees_arbre()})


@Verifie_permission
def Supprimer(request):
    idaffectation = int(request.POST["idaffectation"])
    affectation = AffectationCollaborateur.objects.filter(pk=idaffectation).first()
    if not affectation:
        return JsonResponse({"erreur": "Cette affectation n'existe plus"}, status=401)
    if AffectationCollaborateur.objects.filter(parent=affectation).exists():
        return JsonResponse({"erreur": "Supprimez ou déplacez d'abord les sous-affectations"}, status=401)
    if EvenementCollaborateur.objects.filter(affectation=affectation).exists() or LigneModelePlanningCollaborateur.objects.filter(affectation=affectation).exists():
        return JsonResponse({"erreur": "Cette affectation est utilisée par des évènements ou des modèles de planning : vous pouvez la désactiver"}, status=401)
    chemin = Arbre().Get_chemin(affectation.pk)
    affectation.delete()
    utils_historique.Ajouter(titre="Suppression d'une affectation", detail=chemin, utilisateur=request.user, objet="Affectation", idobjet=idaffectation, classe="AffectationCollaborateur")
    return JsonResponse({"succes": True, "affectations": Get_donnees_arbre()})


class Liste(CustomView, TemplateView):
    menu_code = "affectations_collaborateurs_liste"
    template_name = "parametrage/affectations_collaborateurs.html"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context["page_titre"] = "Affectations"
        context["box_titre"] = "Arborescence des affectations"
        context["box_introduction"] = "Les affectations permettent de rattacher les évènements du planning des collaborateurs à une structure, un groupe, un sous-groupe... sans limite de niveaux. Glissez-déposez une affectation pour la réordonner ou la déplacer sous une autre."
        context["affectations_json"] = json.dumps(Get_donnees_arbre())
        return context
