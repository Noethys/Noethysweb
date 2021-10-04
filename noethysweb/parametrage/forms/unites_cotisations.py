# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Hidden, Fieldset, Div
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import UniteCotisation
from core.widgets import DatePickerWidget
from core.utils import utils_preferences


class Formulaire(FormulaireBase, ModelForm):
    # Label de la prestation
    choix_label = [("DEFAUT", "Label par défaut (Type d'adhésion suivi de l'unité)"), ("PERSO", "Label personnalisé")]
    label_type = forms.TypedChoiceField(label="Label de la prestation", choices=choix_label, initial='DEFAUT', required=True)
    label_perso = forms.CharField(label="Label personnalisé*", required=False)

    # Durée de validité
    choix_validite = [("PERIODE", "Une période"), ("DUREE", "Une durée")]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='PERIODE', required=True)
    validite_jours = forms.IntegerField(label="Jours", required=False)
    validite_mois = forms.IntegerField(label="Mois", required=False)
    validite_annees = forms.IntegerField(label="Années", required=False)

    class Meta:
        model = UniteCotisation
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        type_cotisation = kwargs.pop("categorie")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'unites_cotisations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme unité d'adhésion par défaut"
        if len(UniteCotisation.objects.filter(type_cotisation=type_cotisation)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Importe la durée de validité dans les champs libres
        if self.instance.duree != None:
            # Si validité par durée
            self.fields['validite_type'].initial = "DUREE"
            jours, mois, annees = self.instance.duree.split("-")
            self.fields['validite_jours'].initial = int(jours[1:])
            self.fields['validite_mois'].initial = int(mois[1:])
            self.fields['validite_annees'].initial = int(annees[1:])

        # Importe le label de la prestation
        if self.instance.label_prestation != None:
            self.fields['label_type'].initial = "PERSO"
            self.fields['label_perso'].initial = self.instance.label_prestation

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Fieldset('Généralités',
                Field('nom'),
                Hidden('type_cotisation', value=type_cotisation),
                Field('defaut'),
            ),
            Fieldset('Durée de validité',
                Field('validite_type'),
                Div(
                    Field('validite_annees'),
                    Field('validite_mois'),
                    Field('validite_jours'),
                    id='bloc_duree'
                ),
                Div(
                    Field('date_debut'),
                    Field('date_fin'),
                    id='bloc_periode'
                ),
            ),
            Fieldset('Prestation',
                PrependedText('montant', utils_preferences.Get_symbole_monnaie()),
                Field('label_type'),
                Field('label_perso'),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        """ Convertit les champs de validité en un seul champ duree_validite """
        # Validité par durée
        if self.cleaned_data["validite_type"] == "DUREE":
            jours = int(self.cleaned_data["validite_jours"] or 0)
            mois = int(self.cleaned_data["validite_mois"] or 0)
            annees = int(self.cleaned_data["validite_annees"] or 0)
            if jours == 0 and mois == 0 and annees == 0:
                self.add_error('validite_type', "Vous devez saisir une durée en jours et/ou mois et/ou années")
                return
            self.cleaned_data["duree"] = "j%d-m%d-a%d" % (jours, mois, annees)

        # Validité par date
        if self.cleaned_data["validite_type"] == "PERIODE":
            if self.cleaned_data["date_debut"] == None:
                self.add_error('date_debut', "Vous devez sélectionner une date de début")
                return
            if self.cleaned_data["date_fin"] == None:
                self.add_error('date_fin', "Vous devez sélectionner une date de fin")
                return
            if self.cleaned_data["date_fin"] < self.cleaned_data["date_debut"]:
                self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
                return

        # Label de la prestation
        if self.cleaned_data["label_type"] == "PERSO":
            if self.cleaned_data["label_perso"] in ("", None):
                self.add_error('label_perso', "Vous devez saisir un label personnalisé")
                return
            self.cleaned_data["label_prestation"] = self.cleaned_data["label_perso"]

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// label_type
function On_change_label_type() {
    $('#div_id_label_perso').hide();

    if($(this).val() == 'PERSO') {
        $('#div_id_label_perso').show();
    }
}
$(document).ready(function() {
    $('#id_label_type').change(On_change_label_type);
    On_change_label_type.call($('#id_label_type').get(0));
});


// validite_type
function On_change_validite_type() {
    $('#bloc_duree').hide();
    $('#bloc_periode').hide();

    if($(this).val() == 'DUREE') {
        $('#bloc_duree').show();
    }
    if($(this).val() == 'PERIODE') {
        $('#bloc_periode').show();
    }
}
$(document).ready(function() {
    $('#id_validite_type').change(On_change_validite_type);
    On_change_validite_type.call($('#id_validite_type').get(0));
});

</script>
"""