# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.models import Assurance, PortailRenseignement
from core.widgets import DatePickerWidget
from portail.forms.fiche import FormulaireBase
from core.utils.utils_commandes import Commandes


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Assurance
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }
        help_texts = {
            "assureur": "Sélectionnez un assureur dans la liste proposée.",
            "num_contrat": "Saisissez le numéro de contrat.",
            "date_debut": "Saisissez la date de début d'effet du contrat.",
            "date_fin": "[Optionnel] Saisissez la date de fin du contrat.",
        }

    def __init__(self, *args, **kwargs):
        rattachement = kwargs.pop("rattachement", None)
        mode = kwargs.pop("mode", "MODIFICATION")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_contacts_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # self.helper.use_custom_control = False

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=rattachement.famille_id),
            Hidden('individu', value=rattachement.individu_id),
            Field("assureur"),
            Field("num_contrat"),
            Field("date_debut"),
            Field("date_fin"),
            Commandes(annuler_url="{% url 'portail_individu_assurances' idrattachement=rattachement.pk %}", aide=False, css_class="pull-right"),
        )
