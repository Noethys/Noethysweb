# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.widgets import SelectionActivitesWidget


class Formulaire(FormulaireBase, forms.Form):
    activites = forms.CharField(label="Activités", required=False, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    choix_periode = [(7, "7 jours précédents"), (14, "14 jours précédents"), (21, "21 jours précédents"), (30, "30 jours précédents"), (60, "60 jours précédents"), (90, "90 jours précédents")]
    periode = forms.ChoiceField(label="Période à afficher", choices=choix_periode, initial=14, required=False)
    afficher_jour = forms.BooleanField(label="Afficher aujourd'hui", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_suivi_pointage_parametres"
        self.helper.form_method = "post"

        # Affichage
        self.helper.layout = Layout(
            Field("activites"),
            Field("periode"),
            Field("afficher_jour"),
        )
