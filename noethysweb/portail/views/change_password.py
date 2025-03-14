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
from core.models import Famille


class MyPasswordChangeView(ClassCommuneLogin, auth_views.PasswordChangeView):
    form_class = MyPasswordChangeForm
    success_url = reverse_lazy('password_change_done')
    template_name = "portail/password_change_form.html"

    def get_form_kwargs(self):
        # Appel à la méthode de base pour obtenir les arguments initiaux
        kwargs = super().get_form_kwargs()

        # Ajout de l'utilisateur actuel aux arguments du formulaire
        kwargs['user'] = self.request.user

        return kwargs

    def get_context_data(self, **kwargs):
        context = super(MyPasswordChangeView, self).get_context_data(**kwargs)

        # Fusion du texte des conditions légales avec les valeurs organisateur
        texte_conditions = context['parametres_portail'].get("mentions_conditions_generales", "")
        for nom_champ in ("nom", "rue", "cp", "ville"):
            texte_conditions = texte_conditions.replace("{ORGANISATEUR_%s}" % nom_champ.upper(), getattr(context['organisateur'], nom_champ) or "")
        context['texte_conditions'] = texte_conditions

        return context

    def form_valid(self, form):
        # Vérification de la secquest (applicable pour la famille et individu)
        if "secquest" in form.cleaned_data:
            if hasattr(self.request.user, 'famille'):
                # Si l'utilisateur est associé à une famille, vérifier la sécurité pour la famille
                if not utils_secquest.Check_secquest(famille=self.request.user.famille,
                                                     reponse=form.cleaned_data["secquest"]):
                    form.add_error(None, _("La réponse à la question est erronée"))
                    return self.render_to_response(self.get_context_data(form=form))
            elif hasattr(self.request.user, 'individu'):
                # Si l'utilisateur est un individu, vous pouvez ajouter une logique de vérification ici si nécessaire
                famille = Famille.objects.filter(titulaire_helios_id=self.request.user.individu).first()
                if famille and not utils_secquest.Check_secquest(famille=famille,
                                                                 reponse=form.cleaned_data["secquest"]):
                    form.add_error(None, _("La réponse à la question est erronée"))
                    return self.render_to_response(self.get_context_data(form=form))

        # Sauvegarder le formulaire
        form.save()
        utilisateur = form.user

        # Enregistrement du nouveau mot de passe
        update_session_auth_hash(self.request, utilisateur)
        utilisateur.force_reset_password = False
        utilisateur.date_expiration_mdp = None
        utilisateur.save()

        # Vérification si l'utilisateur est associé à une famille ou à un individu
        if hasattr(utilisateur, 'famille'):
            # Mise à jour des informations de la famille
            utilisateur.famille.internet_mdp = "*****"
            utilisateur.famille.save()

        elif hasattr(utilisateur, 'individu'):
            # Mise à jour des informations de l'individu
            utilisateur.individu.internet_mdp = "*****"
            utilisateur.individu.save()

        return super().form_valid(form)

class MyPasswordChangeDoneView(ClassCommuneLogin, auth_views.PasswordChangeDoneView):
    template_name = "portail/password_change_done.html"
