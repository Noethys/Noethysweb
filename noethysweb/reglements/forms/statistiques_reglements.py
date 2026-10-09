# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import ModeReglement, CompteBancaire
from core.widgets import DateRangePickerWidget


def Get_periode_defaut():
    """ Année scolaire en cours : du 1er septembre au 31 août """
    aujourdhui = datetime.date.today()
    annee = aujourdhui.year if aujourdhui.month >= 9 else aujourdhui.year - 1
    return "%s;%s" % (datetime.date(annee, 9, 1), datetime.date(annee + 1, 8, 31))


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(),
                              help_text="Les règlements sont retenus selon leur date.")
    modes = forms.ModelMultipleChoiceField(label="Modes de règlement", queryset=ModeReglement.objects.all().order_by("label"),
                                           widget=forms.CheckboxSelectMultiple, required=True)
    compte = forms.ModelChoiceField(label="Compte bancaire", queryset=CompteBancaire.objects.all().order_by("nom"), required=False,
                                    empty_label="Tous les comptes")
    comparer = forms.BooleanField(label="Comparer avec la période précédente", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_statistiques_reglements"
        self.helper.form_method = "post"

        self.fields["periode"].initial = Get_periode_defaut()
        self.fields["modes"].initial = list(ModeReglement.objects.values_list("pk", flat=True))

        self.helper.layout = Layout(
            Field("periode"),
            Field("modes", wrapper_class="statistiques_categories"),
            Field("compte"),
            Field("comparer"),
        )
