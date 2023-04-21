# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from django_select2.forms import Select2Widget, ModelSelect2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget
from core.models import CompteBancaire, ModeReglement, Emetteur
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    compte = forms.ModelChoiceField(label="Compte", widget=Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}), queryset=CompteBancaire.objects.none(), required=True)
    mode = forms.ModelChoiceField(label="Mode de règlement", queryset=ModeReglement.objects.all().order_by("label"), widget=ModelSelect2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}, search_fields=['nom__icontains']), required=True)
    emetteur = forms.ModelChoiceField(label="Emetteur", queryset=Emetteur.objects.all().order_by("nom"), widget=ModelSelect2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}, search_fields=['nom__icontains'], dependent_fields={"mode": "mode"}), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Compte bancaire
        self.fields["compte"].queryset = CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")

        self.helper.layout = Layout(
            Fieldset("Sélection des prestations",
                Field("periode"),
            ),
            Fieldset("Paramètres des règlements",
                Field("compte"),
                Field("mode"),
                Field("emetteur"),
            ),
        )
