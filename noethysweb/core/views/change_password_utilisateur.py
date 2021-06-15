# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.forms.change_password_utilisateur import MyPasswordChangeForm
from django.contrib.auth import views as auth_views
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import password_validators_help_text_html
from django.contrib import messages


class View(CustomView, TemplateView, auth_views.PasswordChangeView):
    menu_code = "accueil"
    form_class = MyPasswordChangeForm
    success_url = reverse_lazy('profil_utilisateur')
    template_name = "core/change_password_utilisateur.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Profil"
        context['box_titre'] = "Modification du mot de passe"
        context['box_introduction'] = "Saisissez à deux reprises le mot de passe souhaité en tenant compte des caractéristiques énoncées ci-dessous."
        context['texte_validateurs'] = password_validators_help_text_html()
        return context

    def form_valid(self, form):
        form.save()
        utilisateur = form.user

        # Enregistrement du nouveau mot de passe
        update_session_auth_hash(self.request, utilisateur)

        # Confirmation
        messages.add_message(self.request, messages.SUCCESS, "Le mot de passe a été modifié avec succès")

        return super().form_valid(form)
