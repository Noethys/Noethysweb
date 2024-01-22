# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.views.generic import TemplateView
from django.http import JsonResponse
from core.models import Parametre
from core.views.base import CustomView
from individus.forms.imprimer_liste_inscrits import Formulaire


def get_data_profil(donnees=None, request=None):
    """ Récupère les données à sauvegarder dans le profil de configuration """
    form = Formulaire(donnees, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Les paramètres ne sont pas valides"}, status=401)

    data = form.cleaned_data
    data["activite"] = data["activite"].pk
    data.pop("profil")
    data.pop("date_situation")
    return data


def Generer_pdf(request):
    # Récupération des paramètres
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Veuillez compléter les paramètres."}, status=401)
    if not form.cleaned_data["colonnes_perso"]:
        return JsonResponse({"erreur": "Vous devez créer au moins une colonne."}, status=401)

    # Création du PDF
    from individus.utils import utils_impression_inscrits
    impression = utils_impression_inscrits.Impression(titre="Liste des inscrits", dict_donnees=form.cleaned_data)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=401)
    nom_fichier = impression.Get_nom_fichier()
    return JsonResponse({"nom_fichier": nom_fichier})


class View(CustomView, TemplateView):
    menu_code = "imprimer_liste_inscrits"
    template_name = "individus/imprimer_liste_inscrits.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Imprimer une liste d'inscrits"
        context["box_titre"] = "Imprimer une liste d'inscrits"
        context["box_introduction"] = "Sélectionnez une activité et créez les colonnes du document. Il est possible de mémoriser ces paramètres grâce au profil de configuration."

        # Copie le request_post pour préparer l'application du profil de configuration
        request_post = self.request.POST.copy()
        initial_data = None

        # Sélection du profil de configuration
        if request_post.get("profil"):
            profil = Parametre.objects.filter(idparametre=int(request_post.get("profil"))).first()
            initial_data = json.loads(profil.parametre or "{}")
            initial_data["profil"] = profil.pk
            initial_data["colonnes_perso"] = json.dumps(initial_data["colonnes_perso"])

        # Intégration des formulaires
        context["form"] = Formulaire(data=initial_data, request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data())

        context = {"form": form}
        return self.render_to_response(self.get_context_data(**context))
