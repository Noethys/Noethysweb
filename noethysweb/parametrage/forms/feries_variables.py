# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Ferie, LISTE_MOIS
import datetime


class Formulaire(FormulaireBase, ModelForm):
    jour = forms.IntegerField(min_value=1, max_value=31)
    mois = forms.ChoiceField(choices=LISTE_MOIS)
    annee = forms.IntegerField(label="Année", initial=datetime.date.today().year)

    class Meta:
        model = Ferie
        fields = ['type', 'nom', 'annee', 'jour', 'mois']

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'feries_variables_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'feries_variables_liste' %}"),
            Hidden('type', value='variable'),
            Field('nom'),
            Field('jour'),
            Field('mois'),
            Field('annee'),
        )

    def clean_jour(self):
        if self.cleaned_data['jour'] < 1 or self.cleaned_data['jour'] > 31 :
            raise ValidationError("Le jour doit être compris entre 1 et 31")
        return self.cleaned_data['jour']
