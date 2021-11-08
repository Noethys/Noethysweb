# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Div, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import PortailPeriode, ModeleEmail, CategorieCompteInternet
from core.widgets import DatePickerWidget, DateTimePickerWidget
from django_select2.forms import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    introduction = forms.CharField(label="Introduction", widget=forms.Textarea(attrs={'rows': 3}), required=False)
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=True, widget=DatePickerWidget())
    affichage_date_debut = forms.DateTimeField(label="Date de début*", required=False, widget=DateTimePickerWidget())
    affichage_date_fin = forms.DateTimeField(label="Date de fin*", required=False, widget=DateTimePickerWidget())
    modele = forms.ModelChoiceField(label="Modèle d'Email", queryset=ModeleEmail.objects.filter(categorie="portail_demande_reservation"), required=False, help_text="Laissez vide si vous souhaitez que le modèle par défaut soit automatiquement sélectionné.")
    categories = forms.ModelMultipleChoiceField(label="Sélection de catégories", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}),
                                                queryset=CategorieCompteInternet.objects.all().order_by("nom"), required=False,
                                                help_text="Sélectionnez une ou plusieurs catégories de compte internet.")
    class Meta:
        model = PortailPeriode
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_portail_periodes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=idactivite),
            Fieldset("Généralités",
                Field("nom"),
                Field("introduction"),
            ),
            Fieldset("Période",
                Field("date_debut"),
                Field("date_fin"),
                Field("type_date"),
            ),
            Fieldset("Affichage",
                Field("affichage"),
                Div(
                    Field("affichage_date_debut"),
                    Field("affichage_date_fin"),
                    id="bloc_affichage",
                ),
            ),
            Fieldset("Email de réponse",
                Field("modele"),
            ),
            Fieldset("Préfacturation",
                Field("prefacturation"),
            ),
            Fieldset("Options",
                Field("types_categories"),
                Field("categories"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Période
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return

        # Affichage
        if self.cleaned_data["affichage"] == "PERIODE":
            if not self.cleaned_data["affichage_date_debut"]:
                self.add_error('affichage_date_debut', "Vous devez sélectionner une date de début d'affichage")
                return
            if not self.cleaned_data["affichage_date_fin"]:
                self.add_error('affichage_date_fin', "Vous devez sélectionner une date de fin d'affichage")
                return
            if self.cleaned_data["affichage_date_debut"] > self.cleaned_data["affichage_date_fin"] :
                self.add_error('affichage_date_fin', "La date de fin d'affichage doit être supérieure à la date de début")
                return
        else:
            self.cleaned_data["affichage_date_debut"] = None
            self.cleaned_data["affichage_date_fin"] = None

        # Catégories
        if self.cleaned_data["types_categories"] == "SELECTION":
            if not self.cleaned_data["categories"]:
                self.add_error('categories', "Vous devez sélectionner au moins une catégorie")
                return

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// validite_type
function On_change_affichage() {
    $('#bloc_affichage').hide();
    if($(this).val() == 'PERIODE') {
        $('#bloc_affichage').show();
    }
}
$(document).ready(function() {
    $('#id_affichage').change(On_change_affichage);
    On_change_affichage.call($('#id_affichage').get(0));
});

// types_categories
function On_change_types_categories() {
    $('#div_id_categories').hide();
    if($(this).val() == 'SELECTION') {
        $('#div_id_categories').show();
    }
}
$(document).ready(function() {
    $('#id_types_categories').change(On_change_types_categories);
    On_change_types_categories.call($('#id_types_categories').get(0));
});

</script>
"""
