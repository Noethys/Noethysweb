# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    choix_periode = [(7, "1 semaine"), (14, "2 semaines"), (21, "3 semaines"), (30, "1 mois"), (60, "2 mois"), (90, "3 mois")]
    periode = forms.ChoiceField(label="Période à afficher", choices=choix_periode, initial=14, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_suivi_achats_parametres'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Field("periode"),
        )
