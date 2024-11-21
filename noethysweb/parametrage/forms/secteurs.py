# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Secteur
from core.widgets import ColorPickerWidget


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Secteur
        fields = "__all__"
        widgets = {
            "couleur": ColorPickerWidget(),
        }
        help_texts = {
            "couleur": "Cliquez sur le champ pour afficher le sélecteur de couleur. Cette couleur peut être appliquée dans certaines fonctionnalités de l'application."
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'secteurs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'secteurs_liste' %}"),
            Field('nom'),
            Field("couleur"),
        )
