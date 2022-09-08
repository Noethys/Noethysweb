# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column, Fieldset
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import CompteBancaire, Structure



class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = CompteBancaire
        fields = ['nom', 'numero', 'defaut', 'raison', 'code_etab', 'code_guichet',
                  'cle_rib', 'cle_iban', 'iban', 'bic', 'code_ics', 'code_nne', "dft_titulaire",
                  "dft_iban", 'structure']

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'comptes_bancaires_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme compte par défaut"
        if len(CompteBancaire.objects.all()) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'comptes_bancaires_liste' %}"),
            Fieldset('Généralités',
                Field('nom'),
                Field('defaut'),
            ),
            Fieldset("Coordonnées bancaires",
                Field('numero'),
                Field('code_etab'),
                Field('code_guichet'),
                Field('cle_rib'),
                Field('cle_iban'),
                Field('iban'),
                Field('bic'),
            ),
            Fieldset("Prélèvement",
                Field('code_ics'),
                Field('code_nne'),
            ),
            Fieldset("Compte DFT",
                Field('raison'),
                Field("dft_titulaire"),
                Field("dft_iban"),
            ),
            Fieldset('Structure associée',
                Field('structure'),
            ),
        )

