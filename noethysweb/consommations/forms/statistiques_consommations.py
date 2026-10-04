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
from core.models import LISTE_ETATS_CONSO
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget

ETATS_DEFAUT = ["reservation", "present", "absentj", "absenti"]


def Get_periode_defaut():
    """ Année scolaire en cours : du 1er septembre au 31 août """
    aujourdhui = datetime.date.today()
    annee = aujourdhui.year if aujourdhui.month >= 9 else aujourdhui.year - 1
    return "%s;%s" % (datetime.date(annee, 9, 1), datetime.date(annee + 1, 8, 31))


class Formulaire(FormulaireBase, forms.Form):
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    etats = forms.MultipleChoiceField(label="États pris en compte", choices=[(code, label) for code, label in LISTE_ETATS_CONSO if code != "demande"],
                                      widget=forms.CheckboxSelectMultiple, required=True, initial=ETATS_DEFAUT)
    comparer = forms.BooleanField(label="Comparer avec la période précédente", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_statistiques_consommations"
        self.helper.form_method = "post"

        self.fields["periode"].initial = Get_periode_defaut()

        self.helper.layout = Layout(
            Field("periode"),
            Field("activites"),
            Field("etats", wrapper_class="statistiques_etats"),
            Field("comparer"),
        )

    def clean_activites(self):
        import json
        try:
            selection = json.loads(self.cleaned_data["activites"])
        except Exception:
            raise forms.ValidationError("La sélection des activités n'est pas valide")
        if not selection.get("ids"):
            raise forms.ValidationError("Vous devez sélectionner au moins une activité")
        return self.cleaned_data["activites"]
