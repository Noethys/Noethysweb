# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Facture, LotFactures
from core.widgets import DatePickerWidget, Select_avec_commandes


class Formulaire(FormulaireBase, ModelForm):
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=True, widget=DatePickerWidget())
    date_edition = forms.DateField(label="Date d'émission", required=True, widget=DatePickerWidget())
    date_echeance = forms.DateField(label="Date d'échéance", required=False, widget=DatePickerWidget())
    date_limite_paiement = forms.DateField(label="Date limite de paiement en ligne", required=False, widget=DatePickerWidget())
    lot = forms.ModelChoiceField(label="Lot de factures", queryset=LotFactures.objects.all(), required=False, widget=Select_avec_commandes(
                      {"donnees_extra": {}, "url_ajax": "ajax_modifier_lot_factures",
                       "textes": {"champ": "Nom du lot", "ajouter": "Saisir un lot de factures", "modifier": "Modifier un lot de factures"}}))
    observations = forms.CharField(label="Observations", required=False, widget=forms.Textarea(attrs={"rows": 2}))

    class Meta:
        model = Facture
        fields = ["date_debut", "date_fin", "date_edition", "date_echeance", "lot", "regie", "prefixe", "numero", "date_limite_paiement", "observations"]

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
            Fieldset("Période",
                Field('date_debut'),
                Field('date_fin'),
            ),
            Fieldset("Dates",
                Field('date_edition'),
                Field('date_echeance'),
                Field('date_limite_paiement'),
            ),
            Fieldset("Numéro",
                Field('prefixe'),
                Field('numero'),
            ),
            Fieldset("Options",
                Field('lot'),
                Field('regie'),
                Field('observations'),
            ),
        )


class Formulaire_annulation(FormulaireBase, forms.Form):
    observations = forms.CharField(label="Observations", required=False, help_text="Vous pouvez ajouter un commentaire qui sera mémorisé dans la facture annulée. Il peut s'agir par exemple de la raison de l'annulation.", widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super(Formulaire_annulation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_annulation"
        self.helper.form_method = "post"
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Field("observations"),
        )
