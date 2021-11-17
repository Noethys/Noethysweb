# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import SignatureEmail
from django_summernote.widgets import SummernoteInplaceWidget


class Formulaire(FormulaireBase, ModelForm):
    html = forms.CharField(label="Texte", widget=SummernoteInplaceWidget(attrs={'summernote': {'width': '100%', 'height': '300px'}}))

    class Meta:
        model = SignatureEmail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'signatures_emails_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Fieldset("Généralités",
                Field('nom'),
                Field('structure'),
            ),
            Fieldset("Signature",
                Field('html'),
            ),
        )
