# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Activite, TypeGroupeActivite
from core.widgets import DatePickerWidget
from core.forms.select2 import Select2MultipleWidget
import datetime
from core.widgets import Telephone, CodePostal, Ville, Selection_image


class Formulaire(FormulaireBase, ModelForm):
    # Durée de validité
    choix_validite = [("ILLIMITEE", "Durée illimitée"), ("LIMITEE", "Durée limitée")]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='ILLIMITEE', required=True)
    validite_date_debut = forms.DateField(label="Date de début*", required=False, widget=DatePickerWidget())
    validite_date_fin = forms.DateField(label="Date de fin*", required=False, widget=DatePickerWidget())

    # Groupes d'activités
    groupes_activites = forms.ModelMultipleChoiceField(label="Groupes d'activités", widget=Select2MultipleWidget(), queryset=TypeGroupeActivite.objects.all(), required=False)

    # Nombre max d'inscrits
    choix_nbre_inscrits = [("NON", "Sans limitation du nombre d'inscrits"), ("OUI", "Avec limitation du nombre d'inscrits")]
    type_nbre_inscrits = forms.TypedChoiceField(label="Limitation du nombre d'inscrits", choices=choix_nbre_inscrits, initial="NON", required=False)

    # Logo
    choix_logo = [("ORGANISATEUR", "Identique à celui de l'organisateur"), ("SPECIFIQUE", "Logo spécifique à l'activité")]
    type_logo = forms.TypedChoiceField(label="Logo de l'activité", choices=choix_logo, initial="ORGANISATEUR", required=False)

    # Lien paiement
    choix_pay = [("NON", "Pas de paiement CB via lien externe"), ("OUI", "Paiement CB via lien externe")]
    type_pay = forms.TypedChoiceField(label="Choix de l'option", choices=choix_pay, initial="NON", required=False)

    # Coordonnées
    choix_coords = [("ORGANISATEUR", "Identiques à celles de l'organisateur"), ("SPECIFIQUE", "Coordonnées spécifiques à l'activité")]
    type_coords = forms.TypedChoiceField(label="Coordonnées de l'activité", choices=choix_coords, initial="ORGANISATEUR", required=False)

    class Meta:
        model = Activite
        fields = ["pay", "nom", "abrege", "pay_org", "coords_org", "rue", "cp", "ville", "tel", "fax", "mail", "site", "logo_org", "logo", "code_produit_local", "service1", "service2",
                  "date_debut", "date_fin", "groupes_activites", "nbre_inscrits_max", "inscriptions_multiples", "regie", "code_comptable", "code_analytique", "structure"]
        widgets = {
            'tel': Telephone(),
            'fax': Telephone(),
            'rue': forms.Textarea(attrs={'rows': 2}),
            'cp': CodePostal(attrs={"id_ville": "id_ville"}),
            'ville': Ville(attrs={"id_codepostal"   : "id_cp"}),
            'logo': Selection_image(),
        }
        help_texts = {
            "nom": "Saisissez le nom complet de l'activité.",
            "abrege": "Saisissez le nom abrégé de l'activité (quelques caractères en majuscules).",
            "structure": "Sélectionnez la structure associée à cette activité.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_generalites_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

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

        # Importe la limitation du nombre d'inscrits
        if self.instance.nbre_inscrits_max == None :
            self.fields['type_nbre_inscrits'].initial = "NON"
        else:
            self.fields['type_nbre_inscrits'].initial = "OUI"

        # Importe le logo spécifique
        if self.instance.logo_org == True :
            self.fields['type_logo'].initial = "ORGANISATEUR"
        else:
            self.fields['type_logo'].initial = "SPECIFIQUE"

        # Importe les coordonnées spécifiques
        if self.instance.coords_org == True :
            self.fields['type_coords'].initial = "ORGANISATEUR"
        else:
            self.fields['type_coords'].initial = "SPECIFIQUE"
        
        # Importe le lien de paiement direct
        if self.instance.pay_org ==  True :
            self.fields['type_pay'].initial = "OUI"

        else:
            self.fields['type_pay'].initial = "NON"

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="activites_generalites_modifier", modifier_args="idactivite=activite.idactivite", modifier=True, enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'activites_generalites' idactivite=activite.idactivite %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Fieldset("Généralités",
                Field("nom"),
                Field("abrege"),
                Field("structure"),
            ),
            Fieldset("Durée de validité",
                Field("validite_type"),
                Div(
                    Field("validite_date_debut"),
                    Field("validite_date_fin"),
                    id="bloc_periode"
                ),
            ),
            Fieldset("Groupes d'activités",
                Field("groupes_activites"),
            ),
            Fieldset("Inscriptions",
                Field("type_nbre_inscrits"),
                Field("nbre_inscrits_max"),
                Field("inscriptions_multiples"),
            ),
            Fieldset("Logo",
                Field("type_logo"),
                Field("logo"),
            ),
            Fieldset("Coordonnées",
                Field("type_coords"),
                Div(
                    Field('rue'),
                    Field('cp'),
                    Field('ville'),
                    Field('tel'),
                    Field('fax'),
                    Field('mail'),
                    Field('site'),
                    id='bloc_coords',
                ),
            Fieldset("Paiement CB via un lien externe",
                Field("type_pay"),
                Field("pay"),
            ),
            ),
            Fieldset("Options",
                Field("regie"),
                Field("code_comptable"),
                Field("code_analytique"),
                Field("code_produit_local"),
                Field("service1"),
                Field("service2"),
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

        # Limitation du nombre d'inscrits
        if self.cleaned_data["type_nbre_inscrits"] == "OUI":
            if self.cleaned_data["nbre_inscrits_max"] in (None, 0):
                self.add_error('nbre_inscrits_max', "Vous devez saisir une valeur")
                return
        else:
            self.cleaned_data["nbre_inscrits_max"] = None

        # Logo
        if self.cleaned_data["type_logo"] == "ORGANISATEUR":
            self.cleaned_data["logo_org"] = True
        else:
            if self.cleaned_data["logo"] == None:
                self.add_error('logo', "Vous devez charger un logo")
                return
            self.cleaned_data["logo_org"] = False

        # Coordonnées
        if self.cleaned_data["type_coords"] == "ORGANISATEUR":
            self.cleaned_data["coords_org"] = True
        else:
            self.cleaned_data["coords_org"] = False
    
        # Lien paiement
        if self.cleaned_data["type_pay"] == "OUI":
            self.cleaned_data["pay_org"] = True
            
        else:
            self.cleaned_data["pay_org"] = False
            self.cleaned_data["pay"] = ""
    
        print(f"Value of 'type_pay': {self.cleaned_data['type_pay']}")
        print(f"Value of 'pay' after assignment: {self.cleaned_data['pay']}")
        print(f"Value of 'type_pay' after assignment: {self.cleaned_data['type_pay']}")
        print(f"Value of 'pay_org' after assignment: {self.cleaned_data['pay_org']}")
        print("Clean method finished.")
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

// type_nbre_inscrits
function On_change_type_nbre_inscrits() {
    $('#div_id_nbre_inscrits_max').hide();
    if($(this).val() == 'OUI') {
        $('#div_id_nbre_inscrits_max').show();
    }
}
$(document).ready(function() {
    $('#id_type_nbre_inscrits').change(On_change_type_nbre_inscrits);
    On_change_type_nbre_inscrits.call($('#id_type_nbre_inscrits').get(0));
});

// type_logo
function On_change_type_logo() {
    $('#div_id_logo').hide();
    if($(this).val() == 'SPECIFIQUE') {
        $('#div_id_logo').show();
    }
}
$(document).ready(function() {
    $('#id_type_logo').change(On_change_type_logo);
    On_change_type_logo.call($('#id_type_logo').get(0));
});

// type_pay
function On_change_type_pay() {
    $('#div_id_pay').hide();
    if($(this).val() == 'OUI') {
        $('#div_id_pay').show();
    }
}
$(document).ready(function() {
    $('#id_type_pay').change(On_change_type_pay);
    On_change_type_pay.call($('#id_type_pay').get(0));
});

// type_coords
function On_change_type_coords() {
    $('#bloc_coords').hide();
    if($(this).val() == 'SPECIFIQUE') {
        $('#bloc_coords').show();
    }
}
$(document).ready(function() {
    $('#id_type_coords').change(On_change_type_coords);
    On_change_type_coords.call($('#id_type_coords').get(0));
});


</script>
"""