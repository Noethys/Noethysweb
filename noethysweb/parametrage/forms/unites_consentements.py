# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import UniteConsentement
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = UniteConsentement
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        type_consentement = kwargs.pop("categorie")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'unites_consentements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('type_consentement', value=type_consentement),
            Fieldset('Généralités',
                Field('date_debut'),
                Field('date_fin'),
            ),
            Fieldset("Document numérisé",
                Field('document'),
            ),
        )
