# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.contrib.auth import update_session_auth_hash
from portail.forms.change_password import MyPasswordChangeForm
from portail.views.login import ClassCommuneLogin
from portail.utils import utils_secquest


class MyPasswordChangeView(ClassCommuneLogin, auth_views.PasswordChangeView):
    form_class = MyPasswordChangeForm
    success_url = reverse_lazy('password_change_done')
    template_name = "portail/password_change_form.html"

    def get_context_data(self, **kwargs):
        context = super(MyPasswordChangeView, self).get_context_data(**kwargs)

        # Fusion du texte des conditions légales avec les valeurs organisateur
        texte_conditions = context['parametres_portail'].get("mentions_conditions_generales", "")
        for nom_champ in ("nom", "rue", "cp", "ville"):
            texte_conditions = texte_conditions.replace("{ORGANISATEUR_%s}" % nom_champ.upper(), getattr(context['organisateur'], nom_champ) or "")
        context['texte_conditions'] = texte_conditions

        return context

    def form_valid(self, form):
        # Vérification de la secquest
        if "secquest" in form.cleaned_data:
            if not utils_secquest.Check_secquest(famille=self.request.user.famille, reponse=form.cleaned_data["secquest"]):
                form.add_error(None, _("La réponse à la question est erronée"))
                return self.render_to_response(self.get_context_data(form=form))

        form.save()
        utilisateur = form.user

        # Enregistrement du nouveau mot de passe
        update_session_auth_hash(self.request, utilisateur)

        # Enregistre le champ force_reset_password de l'utilisateur
        utilisateur.force_reset_password = False
        utilisateur.date_expiration_mdp = None
        utilisateur.save()
        utilisateur.famille.internet_mdp = "*****"
        utilisateur.famille.save()

        return super().form_valid(form)


class MyPasswordChangeDoneView(ClassCommuneLogin, auth_views.PasswordChangeDoneView):
    template_name = "portail/password_change_done.html"
