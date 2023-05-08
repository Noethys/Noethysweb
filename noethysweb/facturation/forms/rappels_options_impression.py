# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import copy
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils import utils_parametres


class Formulaire(FormulaireBase, forms.Form):
    memoriser_parametres = forms.BooleanField(label="Mémoriser les paramètres", initial=False, required=False)
    afficher_coupon_reponse = forms.BooleanField(label="Afficher le coupon-réponse", initial=True, required=False)
    afficher_codes_barres = forms.BooleanField(label="Afficher les codes-barres", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        self.memorisation = kwargs.pop("memorisation", True)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'options_impression_form'
        self.helper.form_method = 'post'

        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-md-4'
        # self.helper.field_class = 'col-md-8'

        # Importation des paramètres
        if self.memorisation:
            parametres = {nom: field.initial for nom, field in self.fields.items()}
            del parametres["memoriser_parametres"]
            parametres = utils_parametres.Get_categorie(categorie="impression_rappel", utilisateur=self.request.user, parametres=parametres)
            for nom, valeur in parametres.items():
                self.fields[nom].initial = valeur

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Eléments à afficher",
                Field("afficher_coupon_reponse"),
                Field("afficher_codes_barres"),
            ),
        )

        if self.memorisation:
            self.helper.layout.insert(0,
                Fieldset("Mémorisation",
                    Field("memoriser_parametres"),
                ),
            )

    def clean(self):
        if self.memorisation and self.cleaned_data["memoriser_parametres"]:
            parametres = copy.copy(self.cleaned_data)
            del parametres["memoriser_parametres"]
            utils_parametres.Set_categorie(categorie="impression_rappel", utilisateur=self.request.user, parametres=parametres)
