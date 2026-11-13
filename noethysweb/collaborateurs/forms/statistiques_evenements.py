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
from core.forms.select2 import Select2MultipleWidget
from core.models import TypeEvenementCollaborateur, GroupeCollaborateurs
from core.widgets import DateRangePickerWidget
from collaborateurs.utils.utils_affectations import Arbre


def Get_periode_defaut():
    """ Année scolaire en cours : du 1er septembre au 31 août """
    aujourdhui = datetime.date.today()
    annee = aujourdhui.year if aujourdhui.month >= 9 else aujourdhui.year - 1
    return "%s;%s" % (datetime.date(annee, 9, 1), datetime.date(annee + 1, 8, 31))


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(),
                              help_text="Seule la partie des évènements comprise dans la période est comptée.")
    donnees = forms.ChoiceField(label="Données analysées", choices=[("PLANIFIE", "Planifié"), ("REALISE", "Réalisé")], initial="PLANIFIE", required=True,
                                help_text="En réalisé, le temps comptabilisé utilise les horaires réalisés saisis. Les autres catégories (congés, maladie...) restent sur les horaires planifiés.")
    categories = forms.ModelMultipleChoiceField(label="Catégories d'évènements", queryset=TypeEvenementCollaborateur.objects.all().order_by("nom"),
                                                widget=forms.CheckboxSelectMultiple, required=True)
    affectations = forms.MultipleChoiceField(label="Affectations", choices=[], required=False, widget=Select2MultipleWidget({"data-minimum-input-length": 0}),
                                             help_text="Laissez vide pour toutes les affectations. Les sous-affectations sont incluses.")
    groupes = forms.ModelMultipleChoiceField(label="Groupes de collaborateurs", queryset=GroupeCollaborateurs.objects.all().order_by("nom"), required=False,
                                             widget=Select2MultipleWidget({"data-minimum-input-length": 0}), help_text="Laissez vide pour tous les collaborateurs.")
    comparer = forms.BooleanField(label="Comparer avec la période précédente", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_statistiques_evenements"
        self.helper.form_method = "post"

        self.fields["periode"].initial = Get_periode_defaut()
        self.fields["categories"].initial = list(TypeEvenementCollaborateur.objects.values_list("pk", flat=True))
        self.fields["affectations"].choices = Arbre().Get_choix()

        self.helper.layout = Layout(
            Field("periode"),
            Field("donnees"),
            Field("categories", wrapper_class="statistiques_categories"),
            Field("affectations"),
            Field("groupes"),
            Field("comparer"),
        )

    def clean_affectations(self):
        return [int(valeur) for valeur in self.cleaned_data.get("affectations", [])]
