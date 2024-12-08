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
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    introduction = forms.CharField(label="Introduction", widget=forms.Textarea(attrs={'rows': 3}), required=False, help_text="Il est possible de saisir ici un texte qui sera placé en évidence juste au-dessus du planning des réservations de l'individu. Il peut s'agir par exemple d'une information importante au sujet de la période ou d'un rappel sur les règles de la structure. Exemples : Annulation possible jusqu'à 48h avant, Ne ratez pas notre grande fête de l'été, etc...")
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de début de la période que l'usager pourra réserver.")
    date_fin = forms.DateField(label="Date de fin", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de fin de la période que l'usager pourra réserver.")
    affichage_date_debut = forms.DateTimeField(label="Date de début*", required=False, widget=DateTimePickerWidget(), help_text="Saisissez la date à partir de laquelle cette période apparaîtra sur le portail.")
    affichage_date_fin = forms.DateTimeField(label="Date de fin*", required=False, widget=DateTimePickerWidget(), help_text="Saisissez la date jusqu'à laquelle cette période apparaîtra sur le portail.")
    modele = forms.ModelChoiceField(label="Modèle d'Email", queryset=ModeleEmail.objects.filter(categorie="portail_demande_reservation"), required=False, help_text="Laissez vide si vous souhaitez que le modèle par défaut soit automatiquement sélectionné.")
    categories = forms.ModelMultipleChoiceField(label="Sélection de catégories", widget=Select2MultipleWidget(),
                                                queryset=CategorieCompteInternet.objects.all().order_by("nom"), required=False,
                                                help_text="Sélectionnez une ou plusieurs catégories de compte internet.")
    class Meta:
        model = PortailPeriode
        fields = "__all__"
        help_texts = {
            "nom": "Saisissez un nom significatif et clair qui permettra à l'usager de comprendre de quelle période il s'agit. Exemples : Décembre 2023, Vacances d'été 2024, 1er trimestre 2025, etc...",
            "affichage": "Indiquez si cette période doit être affichée sur le portail en permanence, jamais ou uniquement sur une période donnée. Généralement, on sélectionnera la dernière option.",
            "type_date": "Par défaut, toutes les dates ouvertes de la période sont affichées, mais vous pouvez ici choisir d'afficher uniquement les dates scolaires ou de vacances.",
            "types_categories": "Vous pouvez attribuer cette période uniquement à une sélection de comptes internet.",
            "types_villes": "Vous pouvez attribuer cette période uniquement aux familles résidant ou ne résidant pas sur une ou plusieurs villes données.",
            "villes": "Saisissez en majuscules un ou plusieurs noms de villes séparés par des virgules."
        }

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
        self.fields["affichage_date_debut"].widget.attrs.update({"autocomplete": "off"})
        self.fields["affichage_date_fin"].widget.attrs.update({"autocomplete": "off"})

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
            # Fieldset("Email de réponse",
            #     Field("modele"),
            # ),
            Fieldset("Préfacturation",
                Field("prefacturation"),
            ),
            Fieldset("Filtres",
                Field("types_categories"),
                Field("categories"),
                Field("types_villes"),
                Field("villes"),
            ),
            Fieldset("Options",
                Field("mode_consultation"),
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

        # Villes
        if self.cleaned_data["types_villes"] in ("SELECTION", "SELECTION_INVERSE"):
            if not self.cleaned_data["villes"]:
                self.add_error('villes', "Vous devez saisir au moins une ville")
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

// types_villes
function On_change_types_villes() {
    $('#div_id_villes').hide();
    if ($(this).val() == 'SELECTION') {
        $('#div_id_villes').show();
    }
    if ($(this).val() == 'SELECTION_INVERSE') {
        $('#div_id_villes').show();
    }
}
$(document).ready(function() {
    $('#id_types_villes').change(On_change_types_villes);
    On_change_types_villes.call($('#id_types_villes').get(0));
});

</script>
"""
