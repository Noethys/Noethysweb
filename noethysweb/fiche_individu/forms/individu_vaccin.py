# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Vaccin, Individu
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    date = forms.DateField(label="Date de vaccination", required=True, widget=DatePickerWidget())

    class Meta:
        model = Vaccin
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_vaccins_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "individu") == False:
            individu = Individu.objects.get(pk=idindividu)
        else:
            individu = self.instance.individu

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('page', value="vaccin"),
            Hidden('individu', value=individu.idindividu),
            Field("type_vaccin"),
            Field("date"),
        )
