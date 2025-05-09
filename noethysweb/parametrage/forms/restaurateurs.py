# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Restaurateur
from core.widgets import Telephone, CodePostal, Ville, Rue


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Restaurateur
        fields = "__all__"
        widgets = {
            'tel': Telephone(),
            'rue': Rue(attrs={"id_codepostal": "id_cp", "id_ville": "id_ville"}),
            'cp': CodePostal(attrs={"id_ville": "id_ville"}),
            'ville': Ville(attrs={"id_codepostal": "id_cp"}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'restaurateurs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'restaurateurs_liste' %}"),
            Fieldset("Identification",
                Field('nom'),
            ),
            Fieldset("Coordonnées",
                Field('rue'),
                Field('cp'),
                Field('ville'),
                Field('tel'),
                Field('fax'),
                Field('mail'),
            ),
        )
