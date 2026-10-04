# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import Prestation, TypeQuotient
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget


def Get_periode_defaut():
    """ Année scolaire en cours : du 1er septembre au 31 août """
    aujourdhui = datetime.date.today()
    annee = aujourdhui.year if aujourdhui.month >= 9 else aujourdhui.year - 1
    return "%s;%s" % (datetime.date(annee, 9, 1), datetime.date(annee + 1, 8, 31))


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(),
                              help_text="Les prestations sont retenues selon leur date.")
    categories = forms.MultipleChoiceField(label="Catégories", choices=Prestation.categorie_choix, widget=forms.CheckboxSelectMultiple,
                                           required=True, initial=[code for code, label in Prestation.categorie_choix])
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False, "afficher_toutes": True}),
                                help_text="Avec une sélection d'activités, les prestations sans activité (adhésions, locations, autres) ne sont pas prises en compte.")
    type_quotient = forms.ModelChoiceField(label="Type de quotient familial", queryset=TypeQuotient.objects.all().order_by("nom"), required=False,
                                           empty_label="Tous les types")
    comparer = forms.BooleanField(label="Comparer avec la période précédente", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_statistiques_prestations"
        self.helper.form_method = "post"

        self.fields["periode"].initial = Get_periode_defaut()
        self.fields["activites"].initial = json.dumps({"type": "toutes", "ids": []})

        self.helper.layout = Layout(
            Field("periode"),
            Field("categories", wrapper_class="statistiques_categories"),
            Field("activites"),
            Field("type_quotient"),
            Field("comparer"),
        )

    def clean_activites(self):
        try:
            selection = json.loads(self.cleaned_data["activites"])
        except Exception:
            raise forms.ValidationError("La sélection des activités n'est pas valide")
        if selection.get("type") != "toutes" and not selection.get("ids"):
            raise forms.ValidationError("Vous devez sélectionner au moins une activité ou choisir « Toutes les activités »")
        return self.cleaned_data["activites"]
