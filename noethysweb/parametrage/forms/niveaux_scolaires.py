# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Div, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import NiveauScolaire
from django.db.models import Max


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = NiveauScolaire
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'niveaux_scolaires_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Ordre
        if self.instance.ordre == None:
            max = NiveauScolaire.objects.aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'niveaux_scolaires_liste' %}"),
            Hidden('ordre', value=self.fields['ordre'].initial),
            Field('nom'),
            Field('abrege'),
        )
