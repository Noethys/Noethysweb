# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import ImageFond
from core.utils.utils_commandes import Commandes


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = ImageFond
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'images_fond_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = True

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'images_fond_liste' %}"),
            Fieldset("Généralités",
                Field("titre"),
                Field("image"),
            ),
        )
