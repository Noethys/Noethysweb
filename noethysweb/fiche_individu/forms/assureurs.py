# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.models import Assureur
from core.widgets import Telephone, CodePostal, Ville


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Assureur
        fields = "__all__"
        widgets = {
            'telephone': Telephone(),
            'rue_resid': forms.Textarea(attrs={'rows': 2}),
            'cp_resid': CodePostal(attrs={"id_ville": "id_ville_resid"}),
            'ville_resid': Ville(attrs={"id_codepostal": "id_cp_resid"}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'assureurs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'

        # Affichage
        self.helper.layout = Layout(
            Field('nom'),
            Field('rue_resid'),
            Field('cp_resid'),
            Field('ville_resid'),
            Field('telephone'),
            ButtonHolder(
                Div(
                    HTML("""<button type="button" class="btn btn-primary" id="id_assureur_bouton_valider" title="Valider"><i class="fa fa-check margin-r-5"></i>Valider</button>"""),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"
                ),
            ),
        )
