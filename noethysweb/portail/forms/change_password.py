# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.contrib.auth.forms import SetPasswordForm
from django.utils.translation import gettext as _
from portail.utils import utils_secquest
from core.models import Famille


class MyPasswordChangeForm(SetPasswordForm):
    check_conditions = forms.BooleanField(label="", required=True, initial=False)
    field_order = ['new_password1', 'new_password2', 'check_conditions']

    def __init__(self, user, *args, **kwargs):
        super(MyPasswordChangeForm, self).__init__(user, *args, **kwargs)

        # Ajout des classes CSS et placeholders aux champs de mot de passe
        self.fields['new_password1'].widget.attrs['class'] = "form-control"
        self.fields['new_password1'].widget.attrs['title'] = _("Saisissez un nouveau mot de passe")
        self.fields['new_password1'].widget.attrs['placeholder'] = _("Saisissez un nouveau mot de passe")
        self.fields['new_password2'].widget.attrs['class'] = "form-control"
        self.fields['new_password2'].widget.attrs['title'] = _("Saisissez le nouveau mot de passe une nouvelle fois")
        self.fields['new_password2'].widget.attrs['placeholder'] = _("Saisissez le nouveau mot de passe une nouvelle fois")

        # Vérification si l'utilisateur est une Famille ou un Individu
        famille = None
        if hasattr(user, 'famille'):
            # L'utilisateur est une Famille
            famille = user.famille
        elif hasattr(user, 'individu'):
            # L'utilisateur est un Individu, retrouver la Famille correspondante
            famille = Famille.objects.filter(titulaire_helios_id=user.individu).first()

        # Ajouter le champ de question de sécurité s'il y a une famille et une question de sécurité définie
        if famille and famille.internet_secquest:
            self.fields["secquest"] = utils_secquest.Generation_field_secquest(famille=famille)