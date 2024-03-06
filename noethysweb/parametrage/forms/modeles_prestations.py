# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Row, Column, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences
from core.models import ModelePrestation


class Formulaire(FormulaireBase, ModelForm):
    type_tarif = forms.ChoiceField(label="Type de tarif", choices=[("MONTANT", "Montant unique"), ("QF", "Montant selon le quotient familial")], initial="MONTANT", required=False, help_text="Sélectionnez un type de tarif à appliquer : montant unique ou selon le quotient familial.")

    class Meta:
        model = ModelePrestation
        fields = "__all__"
        widgets = {
            "tarifs": forms.Textarea(attrs={'rows': 5}),
        }
        help_texts = {
            "montant": "Saisissez un montant pour cette prestation.",
            "tarifs": "Saisissez ici une tranche de qf et son montant associé par ligne de la façon suivante : QFMIN-QFMAX=MONTANT. Exemple : <br>0-499=9.50<br>500-950=10.05<br>951-999999=13.90",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_prestations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Type de tarif
        if self.instance.pk:
            if self.instance.tarifs:
                self.fields["type_tarif"].initial = "QF"
            elif self.instance.montant:
                self.fields["type_tarif"].initial = "MONTANT"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_prestations_liste' %}"),
            Fieldset("Généralités",
                Field("categorie"),
                Field("label"),
                Field("public"),
            ),
            Fieldset("Activité",
                Field('activite'),
                Field('categorie_tarif'),
                Field('tarif'),
            ),
            Fieldset('Prestation',
                Field('type_tarif'),
                PrependedText('montant', utils_preferences.Get_symbole_monnaie()),
                Field('tarifs'),
            ),
            Fieldset("Options",
                PrependedText("tva", "%"),
                Field("code_compta"),
            ),
            Fieldset("Structure",
                Field("structure"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
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

// Actualise la liste des catégories de tarifs
function On_change_activite() {
    var idactivite = $("#id_activite").val();
    var idcategorie_tarif = $("#id_categorie_tarif").val();
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_get_categories_tarifs' %}",
        data: {'idactivite': idactivite, 'csrfmiddlewaretoken': "{{ csrf_token }}"},
        success: function (data) { 
            $("#id_categorie_tarif").html(data); 
            $("#id_categorie_tarif").val(idcategorie_tarif);
            if (data == '') {
                $("#div_id_categorie_tarif").hide()
            } else {
                $("#div_id_categorie_tarif").show()
            }
            On_change_categorie_tarif();
        }
    });
};
$(document).ready(function() {
    $('#id_activite').change(On_change_activite);
    On_change_activite.call($('#id_activite').get(0));
});


// Actualise la liste des tarifs
function On_change_categorie_tarif() {
    var idactivite = $("#id_activite").val();
    var idcategorie_tarif = $("#id_categorie_tarif").val();
    var idtarif = $("#id_tarif").val();
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_get_tarifs_prestation' %}",
        data: {
            'idactivite': idactivite, 
            'idcategorie_tarif': idcategorie_tarif,
            'masquer_evenements': "oui", 
            'csrfmiddlewaretoken': "{{ csrf_token }}"
        },
        success: function (data) { 
            $("#id_tarif").html(data); 
            $("#id_tarif").val(idtarif);
            if (data == '') {
                $("#div_id_tarif").hide()
            } else {
                $("#div_id_tarif").show()
            }
        }
    });
};
$(document).ready(function() {
    $('#id_categorie_tarif').change(On_change_categorie_tarif);
    On_change_categorie_tarif.call($('#id_categorie_tarif').get(0));
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
