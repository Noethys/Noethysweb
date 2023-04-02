# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.widgets import ColorPickerWidget
from core.utils.utils_commandes import Commandes
from core.models import TypeEvenementCollaborateur


class Formulaire(FormulaireBase, ModelForm):
    couleur = forms.CharField(label="Couleur", required=True, widget=ColorPickerWidget(), initial="#3c8dbc")

    class Meta:
        model = TypeEvenementCollaborateur
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'types_evenements_collaborateurs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_evenements_collaborateurs_liste' %}"),
            Field("nom"),
            Field("type"),
            Field("observations"),
            Field("couleur"),
        )
