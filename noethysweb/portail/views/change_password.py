# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib.auth import views as auth_views
from portail.forms.change_password import MyPasswordChangeForm
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash
from portail.views.login import ClassCommuneLogin


class MyPasswordChangeView(ClassCommuneLogin, auth_views.PasswordChangeView):
    form_class = MyPasswordChangeForm
    success_url = reverse_lazy('password_change_done')
    template_name = "portail/password_change_form.html"

    def get_context_data(self, **kwargs):
        context = super(MyPasswordChangeView, self).get_context_data(**kwargs)

        # Fusion du texte des conditions légales avec les valeurs organisateur
        texte_conditions = context['parametres_portail'].get("mentions_conditions_generales", "")
        for nom_champ in ("nom", "rue", "cp", "ville"):
            texte_conditions = texte_conditions.replace("{ORGANISATEUR_%s}" % nom_champ.upper(), getattr(context['organisateur'], nom_champ))
        context['texte_conditions'] = texte_conditions

        return context

    def form_valid(self, form):
        form.save()
        utilisateur = form.user

        # Enregistrement du nouveau mot de passe
        update_session_auth_hash(self.request, utilisateur)

        # Enregistre le champ force_reset_password de l'utilisateur
        utilisateur.force_reset_password = False
        utilisateur.save()
        utilisateur.famille.internet_mdp = "*****"
        utilisateur.famille.save()

        return super().form_valid(form)


class MyPasswordChangeDoneView(ClassCommuneLogin, auth_views.PasswordChangeDoneView):
    template_name = "portail/password_change_done.html"
