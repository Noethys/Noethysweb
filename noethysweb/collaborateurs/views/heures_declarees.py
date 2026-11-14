# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Validation des heures réalisées déclarées par les collaborateurs depuis leur espace (écarts avec le planning) """

from django.http import JsonResponse, HttpResponseForbidden
from django.views.generic import TemplateView
from django.db import transaction
from core.views.base import CustomView
from core.models import EvenementCollaborateur
from core.utils import utils_historique
from collaborateurs.utils import utils_planning


def Ecart(evenement=None):
    """ Ecart en minutes entre la durée déclarée et la durée prévue """
    return int(((evenement.declare_fin - evenement.declare_debut) - (evenement.date_fin - evenement.date_debut)).total_seconds() // 60)


def Texte_ecart(minutes=0):
    signe = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    return "%s%dh%02d" % (signe, minutes // 60, minutes % 60)


class View(CustomView, TemplateView):
    menu_code = "heures_declarees_collaborateurs"
    template_name = "collaborateurs/heures_declarees.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Heures déclarées"
        lignes = []
        for evenement in EvenementCollaborateur.objects.select_related("collaborateur", "type_evenement").filter(
                declare_etat="ATTENTE", collaborateur_id__in=utils_planning.Get_ids_modifiables(self.request.user)).order_by("date_debut", "collaborateur__nom"):
            lignes.append({"evenement": evenement, "ecart": Texte_ecart(Ecart(evenement)), "ecart_positif": Ecart(evenement) >= 0})
        context["lignes"] = lignes
        return context


def Decider(request):
    """ Valide (l'horaire déclaré devient l'horaire réalisé) ou refuse des déclarations """
    if not request.user.has_perm("core.heures_declarees_collaborateurs"):
        return HttpResponseForbidden()
    ids = [int(valeur) for valeur in request.POST.get("ids", "").split(";") if valeur.isdigit()]
    valider = request.POST.get("decision") == "valider"
    nbre = 0
    with transaction.atomic():
        for evenement in EvenementCollaborateur.objects.select_for_update().select_related("collaborateur").filter(
                pk__in=ids, declare_etat="ATTENTE", collaborateur_id__in=utils_planning.Get_ids_modifiables(request.user)):
            detail = "%s : déclaré %s-%s" % (evenement.date_debut.strftime("%d/%m/%Y"), evenement.declare_debut.strftime("%Hh%M"), evenement.declare_fin.strftime("%Hh%M"))
            if valider:
                evenement.realise_debut, evenement.realise_fin = evenement.declare_debut, evenement.declare_fin
                evenement.declare_debut = evenement.declare_fin = evenement.declare_etat = None
                evenement.version += 1
            else:
                evenement.declare_etat = "REFUSEE"
            evenement.save()
            utils_historique.Ajouter(titre="Validation d'heures déclarées" if valider else "Refus d'heures déclarées", detail=detail, utilisateur=request.user,
                                     collaborateur=evenement.collaborateur_id, objet="Evènement", idobjet=evenement.pk, classe="EvenementCollaborateur")
            nbre += 1
    return JsonResponse({"message": "%d déclaration%s %s" % (nbre, "s" if nbre > 1 else "", ("validée" if valider else "refusée") + ("s" if nbre > 1 else ""))})
