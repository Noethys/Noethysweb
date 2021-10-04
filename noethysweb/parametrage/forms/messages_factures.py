# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import MessageFacture


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = MessageFacture
        fields = "__all__"
        widgets = {
            'texte': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'messages_factures_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Focus
        self.fields['titre'].widget.attrs.update({'autofocus': 'autofocus'})

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% if request.GET.next %}{{ request.GET.next }}{% else %}{{ view.get_success_url }}{% endif %}"),
            Field("titre"),
            Field("texte"),
            HTML("<input type='hidden' name='next' value='{{ request.GET.next }}'>"),
        )

