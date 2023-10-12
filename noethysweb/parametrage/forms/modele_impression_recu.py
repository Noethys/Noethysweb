# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import Recu


class Formulaire(FormulaireBase, ModelForm):
    signataire = forms.CharField(label="Signataire", required=False)
    intro = forms.CharField(label="Introduction", widget=forms.Textarea(attrs={'rows': 4}), required=True)
    afficher_prestations = forms.BooleanField(label="Inclure la liste des prestations payées avec ce règlement", required=False)

    class Meta:
        model = Recu
        fields = ["signataire", "intro", "afficher_prestations"]

    def __init__(self, *args, **kwargs):
        kwargs.pop("memorisation", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modele_impression_recu_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Introduction
        self.fields["intro"].initial = "Je soussigné(e) {SIGNATAIRE}, certifie avoir reçu pour la famille de {FAMILLE} la somme de {MONTANT}."
        self.fields['intro'].help_text = "Mots-clés disponibles : {SIGNATAIRE}, {FAMILLE}, {MONTANT}, {DATE_REGLEMENT}, {MODE_REGLEMENT}, {NOM_PAYEUR}."

        # Affichage
        self.helper.layout = Layout(
            Field("signataire"),
            Field("intro"),
            Field("afficher_prestations"),
        )
