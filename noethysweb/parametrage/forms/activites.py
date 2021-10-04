# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
import datetime
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset
from crispy_forms.bootstrap import Field, FormActions, PrependedText
from core.forms.base import FormulaireBase
from core.models import Activite


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Activite
        fields = ["nom", "abrege", "date_debut", "date_fin", "structure"]

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_generalites_form'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Field('nom'),
            Field('abrege'),
            Field("structure"),
            Hidden('date_debut', value=datetime.date(1977, 1, 1)),
            Hidden('date_fin', value=datetime.date(2999, 1, 1)),
            FormActions(
                Submit('submit', 'Enregistrer', css_class='btn-primary'),
                HTML("""<a class="btn btn-danger" href="{% url 'activites_liste' %}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""))
        )
