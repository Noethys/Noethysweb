# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget
from core.forms.base import FormulaireBase
from core.models import CategorieInformation


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))
    categories_informations = forms.MultipleChoiceField(label="Catégories d'informations", required=False, widget=Select2MultipleWidget(), choices=[], initial=[], help_text="Sélectionnez les catégories à inclure.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Catégories d'information
        liste_categories = CategorieInformation.objects.all().order_by("nom")
        self.fields["categories_informations"].choices = [(categorie.pk, categorie.nom) for categorie in liste_categories]
        self.fields["categories_informations"].initial = [categorie.pk for categorie in liste_categories if "Alimentation" in categorie.nom]

        self.helper.layout = Layout(
            Field('periode'),
            Field('activites'),
            Field('categories_informations'),
        )
