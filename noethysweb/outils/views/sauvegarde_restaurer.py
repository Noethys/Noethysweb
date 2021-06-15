# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from core.views.base import CustomView
from django.views.generic import TemplateView
from outils.forms.sauvegarde_restaurer import Formulaire
from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from outils.utils import utils_sauvegarde


class View(CustomView, TemplateView):
    menu_code = "sauvegarde_restaurer"
    template_name = "core/crud/edit.html"
    compatible_demo = False

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Sauvegarde"
        context['box_titre'] = "Restaurer une sauvegarde"
        context['box_introduction'] = "Sélectionnez une sauvegarde et cliquez sur le bouton Restaurer. Cette fonctionnalité n'est accessible qu'aux superutilisateurs."
        context['afficher_menu_brothers'] = True
        context['form'] = context.get("form", Formulaire)
        return context

    def post(self, request, **kwargs):
        # Validation du form
        form = Formulaire(request.POST, request.FILES, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        # Vérifie que l'utilisateur est un superutilisateur
        if not self.request.user.is_superuser:
            messages.add_message(request, messages.ERROR, "Vous n'êtes pas autorisé à effectuer cette opération. La restauration est réservée au superutilisateurs")
            return self.render_to_response(self.get_context_data(form=form))

        resultat = utils_sauvegarde.Restauration(form=form)
        if resultat:
            # Si message d'erreur
            messages.add_message(request, messages.ERROR, resultat)
            return self.render_to_response(self.get_context_data(form=form))

        messages.success(request, "La restauration est terminée")
        return HttpResponseRedirect(reverse_lazy("accueil"))
