# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.forms.base import FormulaireBase
import datetime


class Formulaire(FormulaireBase, forms.Form):
    nombre = forms.IntegerField(min_value=1, max_value=50, initial=10)
    annee = forms.IntegerField(label="Année", initial=datetime.date.today().year)
    paques = forms.BooleanField(label="Lundi de Pâques", required=False, initial=True)
    ascension = forms.BooleanField(label="Jeudi de l'Ascension", required=False, initial=True)
    pentecote = forms.BooleanField(label="Lundi de Pentecôte", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Générer", ajouter=False, annuler_url="{% url 'feries_variables_liste' %}"),
            Field('nombre'),
            Field('annee'),
            Field('paques'),
            Field('ascension'),
            Field('pentecote'),
        )

