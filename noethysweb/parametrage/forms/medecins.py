# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column, Fieldset
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Medecin
from core.widgets import Telephone, CodePostal, Ville
from fiche_individu.widgets import CarteOSM


class Formulaire(FormulaireBase, ModelForm):
    carte = forms.ChoiceField(label="Localisation", widget=CarteOSM(), required=False)

    class Meta:
        model = Medecin
        fields = "__all__"
        widgets = {
            'tel_cabinet': Telephone(),
            'tel_mobile': Telephone(),
            'rue_resid': forms.Textarea(attrs={'rows': 2}),
            'cp_resid': CodePostal(attrs={"id_ville": "id_ville_resid"}),
            'ville_resid': Ville(attrs={"id_codepostal": "id_cp_resid"}),
            "memo": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'medecins_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'medecins_liste' %}"),
            Fieldset("Identité",
                Field('nom'),
                Field('prenom'),
            ),
            Fieldset("Coordonnées",
                Field('rue_resid'),
                Field('cp_resid'),
                Field('ville_resid'),
                Field("carte"),
                Field('tel_cabinet'),
                Field('tel_mobile'),
            ),
            Fieldset("Divers",
                Field('memo'),
            ),
        )
