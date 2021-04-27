# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, ButtonHolder, Div, Fieldset
from crispy_forms.bootstrap import Field, InlineCheckboxes, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Individu, Medecin
from django_select2.forms import Select2Widget


class Formulaire(ModelForm):
    medecin = forms.ModelChoiceField(label="Sélectionnez un médecin", widget=Select2Widget({"lang": "fr"}), queryset=Medecin.objects.all(), required=False)

    class Meta:
        model = Individu
        fields = ["medecin"]

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'form_selection_medecin'

        individu = Individu.objects.get(pk=idindividu)
        self.fields["medecin"].initial = individu.medecin

        self.helper.layout = Layout(
            Field("medecin"),
            ButtonHolder(
                Div(
                    Submit('submit', _('Valider'), css_class='btn-primary'),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"
                ),
            ),
        )

