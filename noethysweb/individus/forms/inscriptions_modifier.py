# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.forms.select2 import Select2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Activite, Groupe, CategorieTarif
from core.widgets import DatePickerWidget, Select_activite


class Formulaire_activite(FormulaireBase, forms.Form):
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_activite, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection de l'activité",
                Field("activite"),
            ),
        )


class Formulaire_options(FormulaireBase, forms.Form):
    # action = forms.ChoiceField(label="Action", choices=[("modifier", "Modifier l'inscription existante"), ("creer", "Créer une nouvelle inscription et clôturer l'ancienne")], initial="modifier", required=False)
    action_conso = forms.ChoiceField(label="Action", required=False, choices=[
        ("MODIFIER_AUJOURDHUI", "Modifier les consommations existantes à partir d'aujourd'hui"),
        ("MODIFIER_DATE", "Modifier les consommations existantes à partir d'une date donnée"),
        ("MODIFIER_TOUT", "Modifier toutes les consommations existantes"),
        ("MODIFIER_RIEN", "Ne pas modifier les consommations existantes"),
    ])
    date_application_conso = forms.DateField(label="Date d'application", required=False, widget=DatePickerWidget(), help_text="Renseignez la date de début d'application de la modification sur les consommations.")
    modifier_date_debut = forms.BooleanField(label="Modifier la date de début", required=False)
    date_debut = forms.DateField(label=" ", required=False, widget=DatePickerWidget())
    modifier_date_fin = forms.BooleanField(label="Modifier la date de fin", required=False)
    date_fin = forms.DateField(label=" ", required=False, widget=DatePickerWidget())
    modifier_groupe = forms.BooleanField(label="Modifier le groupe", required=False)
    groupe = forms.ModelChoiceField(label=" ", queryset=Groupe.objects.none(), required=False)
    modifier_categorie_tarif = forms.BooleanField(label="Modifier la catégorie de tarif", required=False)
    categorie_tarif = forms.ModelChoiceField(label=" ", queryset=CategorieTarif.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite", None)
        super(Formulaire_options, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'options_inscription'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Groupe
        self.fields['groupe'].queryset = Groupe.objects.filter(activite_id=idactivite).order_by("ordre")
        if len(self.fields['groupe'].queryset) == 1:
            # S'il n'y a qu'un groupe, on le sélectionne par défaut
            self.fields['groupe'].initial = self.fields['groupe'].queryset.first()

        # Catégorie de tarif
        self.fields['categorie_tarif'].queryset = CategorieTarif.objects.filter(activite_id=idactivite).order_by("nom")
        if len(self.fields['categorie_tarif'].queryset) == 1:
            # S'il n'y a qu'une catégorie, on la sélectionne par défaut
            self.fields['categorie_tarif'].initial = self.fields['categorie_tarif'].queryset.first()

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Nouveaux paramètres de l'inscription",
                Field("modifier_date_debut"),
                Field("date_debut"),
                Field("modifier_date_fin"),
                Field("date_fin"),
                Field("modifier_groupe"),
                Field("groupe"),
                Field("modifier_categorie_tarif"),
                Field("categorie_tarif"),
            ),
            Fieldset("Consommations",
                # Field("action"),
                Field("action_conso"),
                Field("date_application_conso"),
            ),
            Fieldset("Sélection des inscriptions à modifier"),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Date début
        if self.cleaned_data["modifier_date_debut"] and not self.cleaned_data["date_debut"]:
            self.add_error('modifier_date_debut', "Vous devez renseigner la date de début souhaitée")
            return

        # Groupe
        if self.cleaned_data["modifier_groupe"] and not self.cleaned_data["groupe"]:
            self.add_error('modifier_groupe', "Vous devez renseigner le groupe souhaité")
            return

        # Catégorie de tarif
        if self.cleaned_data["modifier_categorie_tarif"] and not self.cleaned_data["categorie_tarif"]:
            self.add_error('modifier_categorie_tarif', "Vous devez renseigner la catégorie de tarif souhaitée")
            return

        # Vérifie qu'une option a été cochée
        if not self.cleaned_data["modifier_date_debut"] and not self.cleaned_data["modifier_date_fin"] and not self.cleaned_data["modifier_groupe"] and not self.cleaned_data["modifier_categorie_tarif"]:
            self.add_error('modifier_categorie_tarif', "Vous devez renseigner au moins un paramètre à appliquer")
            return

        # Date de début d'application pour les consommations
        if self.cleaned_data["action_conso"] == "MODIFIER_DATE" and not self.cleaned_data["date_application_conso"]:
            self.add_error('date_application_conso', "Vous devez renseigner la date de début d'application souhaitée pour les consommations")
            return

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Date début
function On_change_date_debut() {
    $('#div_id_date_debut').hide();
    if ($(this).prop("checked")) {
        $('#div_id_date_debut').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_date_debut').change(On_change_date_debut);
    On_change_date_debut.call($('#id_modifier_date_debut').get(0));
});

// Date fin
function On_change_date_fin() {
    $('#div_id_date_fin').hide();
    if ($(this).prop("checked")) {
        $('#div_id_date_fin').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_date_fin').change(On_change_date_fin);
    On_change_date_fin.call($('#id_modifier_date_fin').get(0));
});

// Groupe
function On_change_groupe() {
    $('#div_id_groupe').hide();
    if ($(this).prop("checked")) {
        $('#div_id_groupe').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_groupe').change(On_change_groupe);
    On_change_groupe.call($('#id_modifier_groupe').get(0));
});

// Catégorie de tarif
function On_change_categorie_tarif() {
    $('#div_id_categorie_tarif').hide();
    if ($(this).prop("checked")) {
        $('#div_id_categorie_tarif').show();
    }
}
$(document).ready(function() {
    $('#id_modifier_categorie_tarif').change(On_change_categorie_tarif);
    On_change_categorie_tarif.call($('#id_modifier_categorie_tarif').get(0));
});

// Affiche de la date de modification
function On_change_action_conso() {
    $('#div_id_date_application_conso').hide();
    if ($("#id_action_conso").val() == 'MODIFIER_DATE') {
        $('#div_id_date_application_conso').show();
    };
}
$(document).ready(function() {
    $('#id_action_conso').on('change', On_change_action_conso);
    On_change_action_conso.call($('#id_action_conso').get(0));
});

</script>
"""
