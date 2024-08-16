# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib import messages
from core.views import crud
from core.models import Famille, Rattachement
from individus.forms.etiquettes import Formulaire_categorie


def Reinitialiser(request):
    # Récupération des données du formulaire
    valeurs_form = json.loads(request.POST.get("form_general"))

    # Catégorie
    form_categorie = Formulaire_categorie(valeurs_form)
    form_categorie.is_valid()
    categorie = form_categorie.cleaned_data["categorie"]

    # Coches
    coches = json.loads(request.POST.get("coches"))
    if not coches:
        return JsonResponse({"erreur": "Veuillez cocher au moins une ligne dans la liste"}, status=401)

    # Mise à jour du champ certification
    if categorie == "famille":
        Famille.objects.filter(pk__in=coches).update(certification_date=None)
    else:
        Rattachement.objects.filter(pk__in=coches).update(certification_date=None)

    messages.add_message(request, messages.SUCCESS, "Les %d certifications cochées ont été réinitialisées" % len(coches))
    return JsonResponse({"success": True})


class Page(crud.Page):
    menu_code = "etiquettes_individus"
    template_name = "individus/certifications.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des certifications"
        context["categorie"] = "famille" if "certifications_familles" in str(context["view"]) else "individu"
        context['form_categorie'] = Formulaire_categorie(categorie=context["categorie"])
        return context

    def post(self, request, **kwargs):
        """ Redirige vers la page individus ou familles """
        form_categorie = Formulaire_categorie(request.POST)
        form_categorie.is_valid()
        return redirect("certifications_%ss" % form_categorie.cleaned_data["categorie"])
