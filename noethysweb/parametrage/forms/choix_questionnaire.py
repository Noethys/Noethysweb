# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.models import QuestionnaireChoix
from core.widgets import ColorPickerWidget


class Formulaire(forms.ModelForm):
    idchoix = forms.CharField(widget=forms.HiddenInput(), required=False)
    index = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = QuestionnaireChoix
        exclude = ["question", "ordre"]
        widgets = {
            "couleur": ColorPickerWidget(),
        }
        help_texts = {
            "couleur": "Cliquez sur le champ pour faire apparaître le sélecteur de couleur. Si vous choisissez une couleur sans choisir d'icône, un rond de la couleur choisie apparaîtra devant le choix.",
            "icone": "Vous pouvez indiquer ici le nom d'un icône Fontawesome. Exemples : circle, music, pencil, star, eye, etc... Vous pouvez trouver facilement la liste des icônes Fontawesome sur internet.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "choix_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Field("idchoix"),
            Field("index"),
            Field("label"),
            Field("couleur"),
            Field("icone"),
            Field("visible"),
        )
