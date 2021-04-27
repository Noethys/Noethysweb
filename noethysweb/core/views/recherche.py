# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.models import Famille, Individu, Payeur, Rattachement
from django.db.models import Q, Value
from functools import reduce
from operator import or_
from django.db.models.functions import Concat
from core.views.menu import GetMenuPrincipal
from core.utils import utils_historique
from django.http import JsonResponse



def Memoriser_recherche(request):
    """ Mémorise l'ouverture de la fiche famille dans l'historique """
    idfamille = int(request.POST.get("idfamille"))
    nom_famille = request.POST.get("nom_famille")
    url = request.POST.get("url")

    # Mémorisation dans historique
    utils_historique.Ajouter(titre="Ouverture d'une fiche famille", detail="", utilisateur=request.user, famille=idfamille)

    # Mémorisation dans session utilisateur
    if "historique_recherche" not in request.session:
        request.session["historique_recherche"] = []
    item = {"idfamille": idfamille, "label": nom_famille, "url": url}
    if item not in request.session["historique_recherche"]:
        request.session["historique_recherche"].append(item)
        if len(request.session["historique_recherche"]) >= 10:
            request.session["historique_recherche"].pop(0)
        request.session.modified = True

    return JsonResponse({"resultat": True})




class View(CustomView, TemplateView):
    menu_code = None
    template_name = "core/recherche.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Résultats de la recherche"
        context['data'] = self.Get_resultats()
        return context

    def Get_resultats(self):
        texte = self.request.GET.get("champ_recherche")
        resultats = {"texte": texte}

        # Recherche dans les individus
        champs = ("nom_complet", "nom_complet_inverse", "individu__nom", "individu__nom_jfille", "individu__prenom", "individu__rue_resid", "individu__cp_resid", "individu__ville_resid", "individu__mail")
        condition = reduce(or_, [Q(**{'{}__icontains'.format(f): texte}) for f in champs], Q())
        queryset = Rattachement.objects.select_related('individu', 'famille').annotate(nom_complet=Concat('individu__nom', Value(' '), 'individu__prenom'), nom_complet_inverse=Concat('individu__prenom', Value(' '), 'individu__nom'))
        resultats["rattachements"] = queryset.filter(condition).order_by("individu__nom", "individu__prenom")[:50]

        # Recherche dans les payeurs
        resultats["payeurs"] = Payeur.objects.select_related('famille').filter(nom__icontains=texte).order_by("nom")[:50]

        # Recherche dans le menu
        resultats["commandes"] = []
        menu_principal = GetMenuPrincipal(user=self.request.user)
        for menu in menu_principal.GetChildren():
            for sous_menu in menu.GetChildren():
                for commande in sous_menu.GetChildren():
                    if texte.lower() in commande.titre.lower():
                        resultats["commandes"].append(commande)

        return resultats