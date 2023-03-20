# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field, PrependedText
from core.models import ComptaVentilation, ComptaAnalytique, ComptaCategorie
from core.widgets import DatePickerWidget
from core.utils import utils_parametres, utils_preferences


class Formulaire(forms.ModelForm):
    idventilation = forms.CharField(widget=forms.HiddenInput(), required=False)
    index = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = ComptaVentilation
        exclude = ["operation",]
        widgets = {
            "date_budget": DatePickerWidget(),
        }
        help_texts = {
            "date_budget": "Cette ventilation apparaîtra sur le budget dont la période contient cette date.",
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        type_operation = kwargs.pop("type", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "ventilation_tresorerie_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Analytique
        self.fields["analytique"].queryset = ComptaAnalytique.objects.filter(Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")
        if not self.instance.pk:
            analytique_defaut = utils_parametres.Get(utilisateur=request.user, nom="analytique", categorie="ventilation_tresorerie", valeur=None)
            if analytique_defaut:
                self.fields["analytique"].initial = analytique_defaut

        # Catégorie
        categories = ComptaCategorie.objects.filter(Q(type=type_operation) & (Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True))).order_by("nom")
        self.fields["categorie"].choices = [(None, "---------")] + [(categorie.pk, categorie.nom) for categorie in categories]

        self.helper.layout = Layout(
            Field("idventilation"),
            Field("index"),
            Field("date_budget"),
            Field("analytique"),
            Field("categorie"),
            PrependedText("montant", utils_preferences.Get_symbole_monnaie()),
        )

    def clean(self):
        if not self.cleaned_data["montant"]:
            self.add_error("montant", "Vous devez saisir un montant.")
            return

        return self.cleaned_data
