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
from core.models import CategorieProduit
from core.widgets import DateRangePickerWidget


def Get_periode_defaut():
    """ Année scolaire en cours : du 1er septembre au 31 août """
    aujourdhui = datetime.date.today()
    annee = aujourdhui.year if aujourdhui.month >= 9 else aujourdhui.year - 1
    return "%s;%s" % (datetime.date(annee, 9, 1), datetime.date(annee + 1, 8, 31))


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(),
                              help_text="Les locations sont retenues dès qu'elles se déroulent en partie sur la période.")
    categories_produits = forms.ModelMultipleChoiceField(label="Catégories de produits", queryset=CategorieProduit.objects.all().order_by("nom"),
                                                         widget=forms.CheckboxSelectMultiple, required=True)
    comparer = forms.BooleanField(label="Comparer avec la période précédente", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_statistiques_locations"
        self.helper.form_method = "post"

        self.fields["periode"].initial = Get_periode_defaut()
        self.fields["categories_produits"].initial = list(CategorieProduit.objects.values_list("pk", flat=True))

        self.helper.layout = Layout(
            Field("periode"),
            Field("categories_produits", wrapper_class="statistiques_categories"),
            Field("comparer"),
        )
