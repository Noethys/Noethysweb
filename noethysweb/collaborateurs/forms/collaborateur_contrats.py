# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django_select2.forms import Select2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import ContratCollaborateur
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = ContratCollaborateur
        fields = "__all__"
        widgets = {
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
            "type_poste": Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "type_poste": "Sélectionnez le type de poste dans la liste proposée.",
            "date_debut": "Saisissez la date de début du contrat.",
            "date_fin": "Saisissez la date de fin de contrat ou laissez vide s'il s'agit d'un contrat à durée indéterminée."
        }

    def __init__(self, *args, **kwargs):
        idcollaborateur = kwargs.pop("idcollaborateur", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'collaborateurs_contrats_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('collaborateur', value=idcollaborateur),
            Fieldset("Généralités",
                Field("type_poste"),
                Field("observations"),
            ),
            Fieldset("Période",
                Field("date_debut"),
                Field("date_fin"),
            ),
        )

    def clean(self):
        # Période
        if self.cleaned_data["date_fin"] and self.cleaned_data["date_fin"] < self.cleaned_data["date_debut"]:
            self.add_error("date_fin", "La date de fin doit être supérieure à la date de début de contrat")
            return
        return self.cleaned_data
