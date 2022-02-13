# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Depot, Reglement
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    nom = forms.CharField(label="Nom du dépôt", required=True)
    date = forms.DateField(label="Date de dépôt", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    verrouillage = forms.BooleanField(label="Verrouillage du dépôt", initial=False, required=False)
    observations = forms.CharField(label="Observations", widget=forms.Textarea(attrs={'rows': 3}), required=False)

    class Meta:
        model = Depot
        fields = ["nom", "date", "compte", "code_compta", "observations", "verrouillage"]

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'depots_reglements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        if not self.instance.pk:
            self.fields['date'].initial = datetime.date.today()

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'depots_reglements_liste' %}", ajouter=False),
            Field('nom'),
            Field('date'),
            Field('compte'),
            Field('code_compta'),
            Field('observations'),
            Field('verrouillage'),
        )
