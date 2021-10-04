# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm, ValidationError
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, Row, Column, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget
from core.models import Vacance


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Vacance
        fields = ['nom', 'annee', 'date_debut', 'date_fin']

        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'vacances_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'vacances_liste' %}"),
            Field('nom'),
            Field('annee'),
            Field('date_debut'),
            Field('date_fin'),
        )

    def clean_date_fin(self):
        if self.cleaned_data['date_debut'] > self.cleaned_data['date_fin'] :
            raise ValidationError("La date de fin doit être supérieure à la date de début.")
        return self.cleaned_data['date_fin']
