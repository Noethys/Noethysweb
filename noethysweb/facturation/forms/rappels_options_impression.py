# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.widgets import ColorPickerWidget
from core.utils import utils_parametres
import copy


class Formulaire(forms.Form):
    memoriser_parametres = forms.BooleanField(label="Mémoriser les paramètres", initial=False, required=False)
    afficher_coupon_reponse = forms.BooleanField(label="Afficher le coupon-réponse", initial=True, required=False)
    afficher_codes_barres = forms.BooleanField(label="Afficher les codes-barres", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'options_impression_form'
        self.helper.form_method = 'post'

        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-md-4'
        # self.helper.field_class = 'col-md-8'

        # Importation des paramètres
        parametres = {nom: field.initial for nom, field in self.fields.items()}
        del parametres["memoriser_parametres"]
        parametres = utils_parametres.Get_categorie(categorie="impression_rappel", parametres=parametres)
        for nom, valeur in parametres.items():
            self.fields[nom].initial = valeur

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Mémorisation",
                Field("memoriser_parametres"),
            ),
            Fieldset("Eléments à afficher",
                Field("afficher_coupon_reponse"),
                Field("afficher_codes_barres"),
            ),
        )

    def clean(self):
        if self.cleaned_data["memoriser_parametres"]:
            parametres = copy.copy(self.cleaned_data)
            del parametres["memoriser_parametres"]
            utils_parametres.Set_categorie(categorie="impression_rappel", parametres=parametres)
