# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.models import Depot
from core.forms.select2 import Select2Widget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    depot = forms.ModelChoiceField(label="Dépôt", widget=Select2Widget(), queryset=Depot.objects.all().order_by("-date"), required=True)
    afficher_tarif_unitaire = forms.BooleanField(label="Afficher détail par tarif unitaire", initial=True, required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Field('depot'),
            Field('afficher_tarif_unitaire'),
        )
