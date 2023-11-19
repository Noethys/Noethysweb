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
from core.models import UniteRemplissage, Unite, Activite
from django.db.models import Max
from core.widgets import DatePickerWidget
import datetime
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    # Durée de validité
    choix_validite = [("ILLIMITEE", "Durée illimitée"), ("LIMITEE", "Durée limitée")]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='ILLIMITEE', required=True)
    validite_date_debut = forms.DateField(label="Date de début*", required=False, widget=DatePickerWidget())
    validite_date_fin = forms.DateField(label="Date de fin*", required=False, widget=DatePickerWidget())

    # Unités
    unites = forms.ModelMultipleChoiceField(label="Unités de consommation associées", widget=Select2MultipleWidget(), queryset=Unite.objects.none(), required=True)

    # Plage horaire
    heure_min = forms.TimeField(label="Heure min", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="La plage horaire permet de comptabiliser uniquement les consommations appartenant à la plage horaire renseignée.")
    heure_max = forms.TimeField(label="Heure max", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = UniteRemplissage
        fields = ["ordre", "activite", "nom", "abrege", "seuil_alerte", "date_debut", "date_fin", "unites", "heure_min", "heure_max",
                  "afficher_page_accueil", "afficher_grille_conso"]

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_unites_remplissage_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Importe la durée de validité
        if self.instance.date_fin in (None, datetime.date(2999, 1, 1)):
            self.fields['validite_type'].initial = "ILLIMITEE"
        else:
            self.fields['validite_type'].initial = "LIMITEE"
            self.fields['validite_date_debut'].initial = self.instance.date_debut
            self.fields['validite_date_fin'].initial = self.instance.date_fin

        # Définit l'activité associée
        if hasattr(self.instance, "activite") == False:
            activite = Activite.objects.get(pk=idactivite)
        else:
            activite = self.instance.activite

        # Unités associées
        self.fields['unites'].queryset = Unite.objects.filter(activite=activite)

        # Ordre
        if self.instance.ordre == None:
            max = UniteRemplissage.objects.filter(activite=activite).aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=activite.idactivite),
            Hidden('ordre', value=self.fields['ordre'].initial),
            Fieldset("Nom de l'unité",
                Field("nom"),
                Field("abrege"),
            ),
            Fieldset("Caractéristiques",
                Field("unites"),
            ),
            Fieldset("Options",
                Field("seuil_alerte"),
                Field("afficher_page_accueil"),
                Field("afficher_grille_conso"),
            ),
            Fieldset("Durée de validité",
                Field("validite_type"),
                Div(
                    Field("validite_date_debut"),
                    Field("validite_date_fin"),
                    id="bloc_periode",
                ),
            ),
            Fieldset("Plage horaire",
                Field("heure_min"),
                Field("heure_max"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Durée de validité
        if self.cleaned_data["validite_type"] == "LIMITEE":
            if self.cleaned_data["validite_date_debut"] == None:
                self.add_error('validite_date_debut', "Vous devez sélectionner une date de début")
                return
            if self.cleaned_data["validite_date_fin"] == None:
                self.add_error('validite_date_fin', "Vous devez sélectionner une date de fin")
                return
            if self.cleaned_data["validite_date_debut"] > self.cleaned_data["validite_date_fin"] :
                self.add_error('validite_date_fin', "La date de fin doit être supérieure à la date de début")
                return
            self.cleaned_data["date_debut"] = self.cleaned_data["validite_date_debut"]
            self.cleaned_data["date_fin"] = self.cleaned_data["validite_date_fin"]
        else:
            self.cleaned_data["date_debut"] = datetime.date(1977, 1, 1)
            self.cleaned_data["date_fin"] = datetime.date(2999, 1, 1)

        return self.cleaned_data



EXTRA_SCRIPT = """
<script>

// validite_type
function On_change_validite_type() {
    $('#bloc_periode').hide();
    if($(this).val() == 'LIMITEE') {
        $('#bloc_periode').show();
    }
}
$(document).ready(function() {
    $('#id_validite_type').change(On_change_validite_type);
    On_change_validite_type.call($('#id_validite_type').get(0));
});

</script>
"""