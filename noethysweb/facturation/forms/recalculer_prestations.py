# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, Profil_configuration
from core.models import Activite
from django_select2.forms import Select2Widget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    activite = forms.ModelChoiceField(label="Activité", widget=Select2Widget({"lang": "fr", "data-width": "100%"}), queryset=Activite.objects.none().order_by("-date_fin"), required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        # Liste les activités liées à la structure actuelle
        self.fields['activite'].queryset = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("-date_fin")

        self.helper.layout = Layout(
            Field('periode'),
            Field('activite'),
        )
