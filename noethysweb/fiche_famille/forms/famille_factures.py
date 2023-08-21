# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder, Div
from crispy_forms.bootstrap import Field, StrictButton, PrependedText, InlineField
from core.utils.utils_commandes import Commandes
from core.models import Facture, LotFactures
from core.widgets import DatePickerWidget, Select_avec_commandes


class Formulaire(FormulaireBase, ModelForm):
    date_edition = forms.DateField(label="Date d'émission", required=True, widget=DatePickerWidget())
    date_echeance = forms.DateField(label="Date d'échéance", required=False, widget=DatePickerWidget())
    lot = forms.ModelChoiceField(label="Lot de factures", queryset=LotFactures.objects.all(), required=False, widget=Select_avec_commandes(
                      {"donnees_extra": {}, "url_ajax": "ajax_modifier_lot_factures",
                       "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot de factures", "modifier": "Modifier un lot de factures"}}))

    class Meta:
        model = Facture
        fields = ["date_edition", "date_echeance", "lot", "regie", "prefixe", "numero"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_factures_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}", ajouter=False),
            Hidden('famille', value=idfamille),
            Field('date_edition'),
            Field('date_echeance'),
            Field('prefixe'),
            Field('numero'),
            Field('lot'),
            Field('regie'),
        )
