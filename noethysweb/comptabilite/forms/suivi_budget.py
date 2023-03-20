# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from django_select2.forms import ModelSelect2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.models import ComptaBudget
from core.forms.base import FormulaireBase


class Widget_budget(ModelSelect2Widget):
    search_fields = ["nom__icontains"]

    def label_from_instance(widget, instance):
        return instance.nom


class Formulaire(FormulaireBase, forms.Form):
    budget = forms.ModelChoiceField(label="Budget", widget=Widget_budget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}), queryset=ComptaBudget.objects.none(), required=True)
    afficher_categories_non_budgetees = forms.BooleanField(label="Inclure les catégories non budgétées", initial=False, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        self.fields["budget"].queryset = ComptaBudget.objects.filter(condition_structure).order_by("date_debut")

        self.helper.layout = Layout(
            Field("budget"),
            Field("afficher_categories_non_budgetees"),
        )
