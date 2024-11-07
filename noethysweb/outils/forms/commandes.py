# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Commande
from core.widgets import DatePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Commande
        fields = "__all__"
        widgets = {
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Généralités",
                Field("nom"),
                Field("modele"),
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset("Options",
                Field("observations"),
            ),
        )

    def clean(self):
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            self.add_error("date_fin", "La date de fin doit être supérieure à la date de début")

        return self.cleaned_data
