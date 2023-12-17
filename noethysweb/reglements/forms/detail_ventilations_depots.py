# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    type_selection = forms.ChoiceField(label="Type de sélection", choices=[("date_depot", "Date de dépôt"),], initial="date_depot", required=False)
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    regroupement_colonne = forms.ChoiceField(label="Colonne", choices=[("mois", "Mois"), ("annee", "Année")], initial="mois", required=False)
    afficher_detail = forms.BooleanField(label="Afficher le détail des prestations", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Fieldset("Données",
                Field("type_selection"),
                Field("periode"),
            ),
            Fieldset("Options",
                Field("regroupement_colonne"),
                Field("afficher_detail"),
            ),
        )
