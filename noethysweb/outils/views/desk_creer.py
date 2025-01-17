# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, time
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.conf import settings
from core.views.base import CustomView
from outils.forms.desk_creer import Formulaire


def Generer(request):
    """ Créer un fichier Noethysweb Desk """
    time.sleep(1)

    # Vérifie que l'utilisateur est un administrateur
    if not request.user.is_superuser:
        return JsonResponse({"erreur": "Accès réservé aux administrateurs"}, status=401)

    # Validation du formulaire
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["<b>%s</b> : %s " % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ", ".join(messages_erreurs)}, status=401)

    # Vérification du mot de passe d'autorisation
    if not settings.SECRET_EXPORT_DESK:
        return JsonResponse({"erreur": "Le code d'autorisation n'a pas été paramétré"}, status=401)

    if form.cleaned_data["mdp_autorisation"] != settings.SECRET_EXPORT_DESK:
        return JsonResponse({"erreur": "Code d'autorisation erroné"}, status=401)

    # Génération du fichier
    try:
        from outils.utils import utils_export_desk
        desk = utils_export_desk.Desk()
        desk.Generer(mdp=form.cleaned_data["mdp_fichier"])
        desk.Envoyer_storage()
    except Exception as err:
        return JsonResponse({"erreur": str(err)}, status=401)
    return JsonResponse({"success": True})


class View(CustomView, TemplateView):
    menu_code = "desk_creer"
    template_name = "outils/desk_creer.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Sauvegardes"
        context['box_titre'] = "Récupérer les données"
        context['box_introduction'] = "_"
        context['afficher_menu_brothers'] = True
        context["form"] = Formulaire(request=self.request)
        return context

    def test_func_page(self):
        if not self.request.user.is_superuser or not settings.SECRET_EXPORT_DESK:
            return False
        return True