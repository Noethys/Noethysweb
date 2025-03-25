# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, time
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from parametrage.forms.api_particulier import Formulaire
from individus.utils import utils_api_particulier


def Saisir_token(request):
    time.sleep(1)

    # Validation du formulaire
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["<b>%s</b> : %s " % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ", ".join(messages_erreurs)}, status=401)

    token = form.cleaned_data["token"]

    # Vérification de la validité du token auprès de l'API
    if not utils_api_particulier.Check_token(token):
        return JsonResponse({"erreur": "Ce token n'est pas valide"}, status=401)

    # Création du code d'autorisation
    nbre_caracteres_code = 5
    code_autorisation = token[-nbre_caracteres_code:]

    # Enregistrement du token
    request.user.token_api_particulier = token[:-nbre_caracteres_code]
    request.user.save()

    # MAJ des codes INSEE des villes de naissance de tous les individus
    from individus.utils import utils_individus
    utils_individus.Maj_insee_ville_naiss_tous_individus()

    return JsonResponse({"success": True, "code_autorisation": code_autorisation})


def Supprimer_token(request):
    """ Suppression du token """
    request.user.token_api_particulier = None
    request.user.save()
    return JsonResponse({"success": True})


class View(CustomView, TemplateView):
    menu_code = "api_particulier_parametrer"
    template_name = "parametrage/api_particulier.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "API particulier"
        context['box_titre'] = "Paramétrer l'accès à API Particulier"
        context['box_introduction'] = "_"
        context['afficher_menu_brothers'] = True
        context["form"] = Formulaire(request=self.request)
        context["token_exists"] = self.request.user.token_api_particulier != None
        return context
