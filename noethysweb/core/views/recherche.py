# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from functools import reduce
from operator import or_
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from core.views.base import CustomView
from core.models import Payeur, Rattachement, Collaborateur
from core.views.menu import GetMenuPrincipal
from core.utils import utils_historique


def Memoriser_recherche(request):
    """ AJAX : Mémorise l'ouverture de la fiche famille dans l'historique """
    idfamille = int(request.POST.get("idfamille"))
    nom_famille = request.POST.get("nom_famille")
    url = request.POST.get("url")
    Memorise_famille(request=request, idfamille=idfamille, nom_famille=nom_famille, url=url)
    return JsonResponse({"resultat": True})


def Memorise_famille(request=None, idfamille=None, nom_famille=None, url=None):
    """ Mémorisation d'une famille """
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


class View(CustomView, TemplateView):
    menu_code = None
    template_name = "core/recherche.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Résultats de la recherche"
        context['data'] = self.resultats
        return context

    def get(self, request, *args, **kwargs):
        """ Affichage direct de la fiche famille en cas de réponse unique """
        self.resultats = self.Get_resultats()
        if "reponse_unique_famille" in self.resultats:
            rattachement = self.resultats["reponse_unique_famille"]
            url = str(reverse_lazy("famille_resume", kwargs={'idfamille': rattachement.famille_id}))
            Memorise_famille(request=request, idfamille=rattachement.famille_id, nom_famille=rattachement.famille.nom, url=url)
            return redirect(url)
        if "reponse_unique_collaborateur" in self.resultats:
            collaborateur = self.resultats["reponse_unique_collaborateur"]
            return redirect(str(reverse_lazy("collaborateur_resume", kwargs={'idcollaborateur': collaborateur.pk})))
        return super().get(request, *args, **kwargs)

    def Get_resultats(self):
        texte = self.request.GET.get("champ_recherche")
        resultats = {"texte": texte}

        # Recherche dans les individus
        champs = ("nom_complet", "nom_complet_inverse", "individu__nom", "individu__nom_jfille", "individu__prenom")
        condition = reduce(or_, [Q(**{'{}__icontains'.format(f): texte}) for f in champs], Q())
        queryset = Rattachement.objects.select_related('individu', 'famille').annotate(nom_complet=Concat('individu__nom', Value(' '), 'individu__prenom'), nom_complet_inverse=Concat('individu__prenom', Value(' '), 'individu__nom'))
        resultats["rattachements"] = queryset.filter(condition).order_by("individu__nom", "individu__prenom")[:50]

        # Recherche dans les payeurs
        resultats["payeurs"] = Payeur.objects.select_related('famille').filter(nom__icontains=texte).order_by("nom")[:50]

        # Recherche dans les collaborateurs
        champs = ("nom_complet", "nom_complet_inverse", "nom", "nom_jfille", "prenom")
        condition = reduce(or_, [Q(**{'{}__icontains'.format(f): texte}) for f in champs], Q())
        queryset = Collaborateur.objects.annotate(nom_complet=Concat('nom', Value(' '), 'prenom'), nom_complet_inverse=Concat('prenom', Value(' '), 'nom'))
        resultats["collaborateurs"] = queryset.filter(condition).order_by("nom", "prenom")[:50]

        # Recherche dans le menu
        resultats["commandes"] = []
        menu_principal = GetMenuPrincipal(user=self.request.user)
        for menu in menu_principal.GetChildren():
            for sous_menu in menu.GetChildren():
                for commande in sous_menu.GetChildren():
                    if texte.lower() in commande.titre.lower():
                        resultats["commandes"].append(commande)

        # Si une seule famille trouvée :
        if resultats["rattachements"] and not resultats["payeurs"] and not resultats["commandes"] and not resultats["collaborateurs"]:
            familles = {rattachement.famille_id: True for rattachement in resultats["rattachements"]}
            if len(familles) == 1:
                resultats["reponse_unique_famille"] = resultats["rattachements"].first()

        # Si un seul collaborateur trouvé :
        if len(resultats["collaborateurs"]) == 1 and not resultats["payeurs"] and not resultats["commandes"] and not resultats["rattachements"]:
            resultats["reponse_unique_collaborateur"] = resultats["collaborateurs"].first()

        return resultats
