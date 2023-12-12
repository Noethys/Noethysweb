# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.utils.translation import gettext as _
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from core.models import Individu
from core.widgets import DatePickerWidget
from core.widgets import CodePostal, Ville
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):
    date_naiss = forms.DateField(label="Date", required=False, widget=DatePickerWidget())

    class Meta:
        model = Individu
        fields = ["civilite", "nom", "nom_jfille", "prenom", "date_naiss", "cp_naiss", "ville_naiss", "type_sieste"]
        widgets = {
            'cp_naiss': CodePostal(attrs={"id_ville": "id_ville_naiss"}),
            'ville_naiss': Ville(attrs={"id_codepostal": "id_cp_naiss"}),
        }

    def __init__(self, *args, **kwargs):
        self.rattachement = kwargs.pop("rattachement", None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "individu_identite"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_identite_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Help_texts pour le mode édition
        self.help_texts = {
            "civilite": _("Sélectionnez une civilité dans la liste déroulante."),
            "nom": _("Saisissez le nom de famille en majuscules."),
            "prenom": _("Saisissez le prénom en minuscules avec la première lettre majuscule."),
            "date_naiss": _("Saisissez la date de naissance au format JJ/MM/AAAA."),
            "cp_naiss": _("Saisissez le code postal, patientez une seconde et sélectionnez la ville dans la liste déroulante."),
            "ville_naiss": _("Saisissez le nom de la ville, patientez une seconde et sélectionnez la ville dans la liste déroulante."),
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": _("Etat-civil"), "champs": ["civilite", "nom", "prenom"]},
            {"titre": _("Naissance"), "champs": ["date_naiss", "cp_naiss", "ville_naiss"]},
            {"titre": _("Divers"), "champs": ["type_sieste"]},
        ]

        # Préparation du layout
        self.Set_layout()
        self.helper.layout.append(HTML(EXTRA_SCRIPT))


EXTRA_SCRIPT = """
<script>

// civilite
function On_change_civilite() {
    $('#div_id_nom_jfille').hide();
    $('#div_id_prenom').hide();
    if($(this).val() == 3) {
        $('#div_id_nom_jfille').show();
    };
    if($(this).val() < 6) {
        $('#div_id_prenom').show();
    }
}
$(document).ready(function() {
    $('#id_civilite').change(On_change_civilite);
    On_change_civilite.call($('#id_civilite').get(0));
});


// deces
function On_change_deces() {
    $('#div_id_annee_deces').hide();
    if ($(this).prop("checked")) {
        $('#div_id_annee_deces').show();
    }
}
$(document).ready(function() {
    $('#id_deces').on('change', On_change_deces);
    On_change_deces.call($('#id_deces').get(0));
});

</script>
"""