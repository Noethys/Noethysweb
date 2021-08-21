# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.models import Individu, PortailRenseignement, TypeMaladie
from django_select2.forms import Select2MultipleWidget
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):
    maladies = forms.ModelMultipleChoiceField(label="Maladies", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), queryset=TypeMaladie.objects.all().order_by("nom"), required=False)

    class Meta:
        model = Individu
        fields = ["maladies"]

    def __init__(self, *args, **kwargs):
        self.rattachement = kwargs.pop("rattachement", None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "individu_maladies"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_maladies_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Help_texts pour le mode édition
        self.help_texts = {
            "maladies": "Sélectionnez les maladies contractées par l'individu dans la liste déroulante.",
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": "Maladies", "champs": ["maladies"]},
        ]

        # Préparation du layout
        self.Set_layout()
