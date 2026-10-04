# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import TypeCotisation
from core.widgets import DateRangePickerWidget


def Get_periode_defaut():
    """ Année scolaire en cours : du 1er septembre au 31 août """
    aujourdhui = datetime.date.today()
    annee = aujourdhui.year if aujourdhui.month >= 9 else aujourdhui.year - 1
    return "%s;%s" % (datetime.date(annee, 9, 1), datetime.date(annee + 1, 8, 31))


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(),
                              help_text="Les adhésions valides sur au moins une partie de la période sont prises en compte.")
    types_cotisations = forms.ModelMultipleChoiceField(label="Types d'adhésions", queryset=TypeCotisation.objects.none(),
                                                       widget=forms.CheckboxSelectMultiple, required=True)
    comparer = forms.BooleanField(label="Comparer avec la période précédente", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_statistiques_cotisations"
        self.helper.form_method = "post"

        # Types d'adhésions accessibles à l'utilisateur
        condition_structure = Q(structure__isnull=True)
        if self.request:
            condition_structure |= Q(structure__in=self.request.user.structures.all())
        types = TypeCotisation.objects.filter(condition_structure).order_by("nom")
        self.fields["types_cotisations"].queryset = types

        # Valeurs initiales
        self.fields["periode"].initial = Get_periode_defaut()
        self.fields["types_cotisations"].initial = types

        self.helper.layout = Layout(
            Field("periode"),
            Field("types_cotisations", wrapper_class="liste_types_cotisations"),
            Field("comparer"),
        )
