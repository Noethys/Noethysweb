# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from portail.forms.reset_password import MyPasswordResetForm, MySetPasswordForm
from portail.views.login import ClassCommuneLogin
from portail.utils import utils_secquest


class MyPasswordResetView(ClassCommuneLogin, auth_views.PasswordResetView):
    email_template_name = "portail/password_reset_email.html"
    form_class = MyPasswordResetForm
    subject_template_name = "portail/password_reset_subject.txt"
    success_url = reverse_lazy('password_reset_done')
    template_name = "portail/reset_password.html"

    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }
        resultat = form.save(**opts)

        # Affiche l'erreur rencontrée dans le form
        if resultat != True:
            form.add_error(None, resultat)
            return super(MyPasswordResetView, self).form_invalid(form)

        return super().form_valid(form)


class MyPasswordResetDoneView(ClassCommuneLogin, auth_views.PasswordResetDoneView):
    template_name = "portail/password_reset_done.html"


class MyPasswordResetConfirmView(ClassCommuneLogin, auth_views.PasswordResetConfirmView):
    template_name = "portail/password_reset_confirm.html"
    form_class = MySetPasswordForm

    def form_valid(self, form):
        # Vérification de la secquest
        if "secquest" in form.cleaned_data:
            if not utils_secquest.Check_secquest(famille=self.user.famille, reponse=form.cleaned_data["secquest"]):
                form.add_error(None, "La réponse à la question est erronée")
                return self.render_to_response(self.get_context_data(form=form))

        return super().form_valid(form)


class MyPasswordResetCompleteView(ClassCommuneLogin, auth_views.PasswordResetCompleteView):
    template_name = "portail/password_reset_complete.html"
