# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from core.widgets import DateRangePickerWidget, Select_activite
from core.models import Activite
from core.forms.base import FormulaireBase

class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)
    etats = forms.MultipleChoiceField(required=True, widget=Select2MultipleWidget(), choices=[("reservation", "Réservation"), ("present", "Présent"), ("attente", "Attente"), ("absentj", "Absence justifiée"), ("absenti", "Absence injustifiée")], initial=["reservation", "present"])
    utiliser_equiv_heures = forms.BooleanField(label="Utiliser les équivalences en heures si elles existent", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request

        self.helper.layout = Layout(
            Field('periode'),
            Field('activite'),
            Field('etats'),
            Field('utiliser_equiv_heures'),
        )
