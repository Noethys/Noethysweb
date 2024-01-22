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
    label_perso = forms.CharField(label="Label personnalisé*", required=False, help_text="Saisissez le label de prestation souhaité. Exemple : Adhésion annuelle.")

    # Durée de validité
    choix_validite = [("PERIODE", "Une période"), ("DUREE", "Une durée")]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='PERIODE', required=True)
    validite_jours = forms.IntegerField(label="Jours", required=False)
    validite_mois = forms.IntegerField(label="Mois", required=False)
    validite_annees = forms.IntegerField(label="Années", required=False)

    # Tarif
    type_tarif = forms.ChoiceField(label="Type de tarif", choices=[("GRATUIT", "Gratuit"), ("MONTANT", "Montant unique"), ("QF", "Montant selon le quotient familial")], initial="MONTANT", required=False, help_text="Sélectionnez un type de tarif à appliquer : montant unique ou selon le quotient familial.")

    class Meta:
        model = UniteCotisation
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
            "tarifs": forms.Textarea(attrs={'rows': 5}),
        }
        help_texts = {
            "montant": "Saisissez un montant pour cette unité d'adhésion.",
            "tarifs": "Saisissez ici une tranche de qf et son montant associé par ligne de la façon suivante : QFMIN-QFMAX=MONTANT. Exemple : <br>0-499=9.50<br>500-950=10.05<br>951-999999=13.90",
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

        # Validité
        self.fields["validite_jours"].widget.attrs.update({"min": 0})
        self.fields["validite_mois"].widget.attrs.update({"min": 0})
        self.fields["validite_annees"].widget.attrs.update({"min": 0})

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme unité d'adhésion par défaut"
        if len(UniteCotisation.objects.filter(type_cotisation=type_cotisation)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Importe la durée de validité dans les champs libres
        if self.instance.duree != None:
            # Si validité par durée
            self.fields['validite_type'].initial = "DUREE"
            try:
                jours, mois, annees = self.instance.duree.split("-")
                self.fields['validite_jours'].initial = int(jours[1:])
                self.fields['validite_mois'].initial = int(mois[1:])
                self.fields['validite_annees'].initial = int(annees[1:])
            except:
                pass

        # Importe le label de la prestation
        if self.instance.label_prestation != None:
            self.fields['label_type'].initial = "PERSO"
            self.fields['label_perso'].initial = self.instance.label_prestation

        # Type de tarif
        if self.instance.pk:
            if self.instance.tarifs:
                self.fields["type_tarif"].initial = "QF"
            elif self.instance.montant:
                self.fields["type_tarif"].initial = "MONTANT"

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
                Field('type_tarif'),
                PrependedText('montant', utils_preferences.Get_symbole_monnaie()),
                Field('tarifs'),
                Field('label_type'),
                Field('label_perso'),
            ),
            Fieldset("Préfacturation",
                Field("prefacturation"),
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

        # Type de tarifs
        if self.cleaned_data.get("type_tarif") == "MONTANT":
            self.cleaned_data["tarifs"] = None
            if self.cleaned_data.get("montant") in (None, ""):
                self.add_error("montant", "Vous devez saisir un montant pour la prestation")

        if self.cleaned_data.get("type_tarif") == "QF":
            self.cleaned_data["montant"] = 0.0
            if not self.cleaned_data.get("tarifs"):
                self.add_error("tarifs", "Vous devez saisir au moins un tarif")
            else:
                resultat = self.Verifie_coherence_tarifs(tarifs=self.cleaned_data["tarifs"])
                if resultat != True:
                    self.add_error("tarifs", resultat)

        return self.cleaned_data

    def Verifie_coherence_tarifs(self, tarifs=""):
        for num_ligne, ligne in enumerate(tarifs.splitlines(), start=1):
            try:
                tranches, montant = ligne.split("=")
                qfmin, qfmax = tranches.split("-")
                qfmin, qfmax, montant = float(qfmin), float(qfmax), float(montant)
            except:
                return "La ligne tarifaire %d semble mal formatée : Vérifiez les valeurs saisies." % num_ligne
            if qfmin > qfmax:
                return "Le QF min est supérieur au QF max sur la ligne %d !" % num_ligne

        return True


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


// Type de tarif
function On_change_type_tarif() {
    $('#div_id_montant').hide();
    $('#div_id_tarifs').hide();
    if($(this).val() == 'MONTANT') {
        $('#div_id_montant').show();
    }
    if($(this).val() == 'QF') {
        $('#div_id_tarifs').show();
    }
}
$(document).ready(function() {
    $('#id_type_tarif').change(On_change_type_tarif);
    On_change_type_tarif.call($('#id_type_tarif').get(0));
});

</script>
"""