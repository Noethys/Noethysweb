# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.db.models import Max
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Div, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.widgets import DatePickerWidget
from core.forms.select2 import Select2MultipleWidget
from core.utils.utils_commandes import Commandes
from core.models import UniteRemplissage, Unite, Activite


class Formulaire(FormulaireBase, ModelForm):
    # Durée de validité
    choix_validite = [("ILLIMITEE", "Durée illimitée"), ("LIMITEE", "Durée limitée")]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='ILLIMITEE', required=True, help_text="""Généralement, cette optin sera toujours
                                            définie sur 'Illimitée', sauf si vous souhaitez masquer cette unité de remplissage à partir d'une date donnée dans la grille des consommations
                                            (Si elle est devenue obsolète par exemple).""")
    validite_date_debut = forms.DateField(label="Date de début*", required=False, widget=DatePickerWidget())
    validite_date_fin = forms.DateField(label="Date de fin*", required=False, widget=DatePickerWidget())

    # Unités
    unites = forms.ModelMultipleChoiceField(label="Unités de consommation associées", widget=Select2MultipleWidget(), queryset=Unite.objects.none(), required=True, help_text="""
                                            Sélectionnez obligatoirement une ou plusieurs unités de consommation à additionner. Exemples : Sélectionnez une unité 'Journée' et une
                                            unité 'Matinée' pour obtenir le nombre d'individus total prévus sur une matinée. Pour une activité simple, vous pouvez également par exemple
                                            sélectionner une unité de consommation 'Atelier' pour afficher uniquement le nombre d'individus prévus sur cette unité.""")

    # Plage horaire
    heure_min = forms.TimeField(label="Heure min", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="""
                                La plage horaire permet de comptabiliser uniquement les consommations appartenant à la plage horaire renseignée. A utiliser uniquement
                                si vous utilisez des unités de consommation de type Horaire ou Multihoraires. Vous pouvez ainsi créer par exemple des unités de remplissage
                                telles que '7h30-8h', '8h-8h30', '8h30-9h' afin d'obtenir le total des individus prévus sur chacun de ces créneaux horaires.""")
    heure_max = forms.TimeField(label="Heure max", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = UniteRemplissage
        fields = ["ordre", "activite", "nom", "abrege", "seuil_alerte", "date_debut", "date_fin", "unites", "heure_min", "heure_max",
                  "afficher_page_accueil", "afficher_grille_conso"]
        help_texts = {
            "afficher_page_accueil": "A décocher uniquement si vous souhaitez que cette unité de remplissage n'apparaisse plus dans le widget 'Suivi des consommations' de la page d'accueil.",
            "afficher_grille_conso": "A décocher uniquement si vous souhaitez que cette unité de remplissage n'apparaisse plus dans la grille des consommations de chaque individu.",
        }

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