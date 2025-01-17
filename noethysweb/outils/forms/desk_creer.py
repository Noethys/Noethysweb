# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.password_validation import validate_password
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    mdp_autorisation = forms.CharField(label="Quel est votre code d'autorisation ?", required=True, help_text="Ce mot de passe vous a été fourni par votre installateur Noethysweb.")
    mdp_fichier = forms.CharField(label="Quel mot de passe souhaitez-vous appliquer au fichier ?", widget=forms.PasswordInput, validators=[validate_password], required=True, help_text="Ce mot de passe sera utilisé pour chiffrer le fichier d'export. Conservez-le bien pour pouvoir déchiffrer le fichier. ")
    mdp_fichier_bis = forms.CharField(label="Confirmation du mot de passe", widget=forms.PasswordInput, required=True, help_text="Saisissez le mot de passe souhaité une seconde fois.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_desk_creer"
        self.helper.form_method = "post"

        # Ajoute les règles de validation du mot de passe au help_text
        self.fields["mdp_fichier"].help_text += " ".join(password_validation.password_validators_help_texts())

        # Affichage
        self.helper.layout = Layout(
            Field("mdp_autorisation"),
            Field("mdp_fichier"),
            Field("mdp_fichier_bis"),
        )

    def clean(self):
        if "mdp_fichier" in self.cleaned_data and self.cleaned_data["mdp_fichier"] != self.cleaned_data["mdp_fichier_bis"]:
            self.add_error("date_fin", "Vous avez mal saisi le mot de passe la seconde fois.")
        return self.cleaned_data
