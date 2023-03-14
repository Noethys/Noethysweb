# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset
from crispy_forms.bootstrap import Field, PrependedText, TabHolder, Tab
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import TarifProduit
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    # Dates de validité
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget())

    # Label prestation
    choix_label = [("NOM_TARIF", "Nom du produit"), ("DESCRIPTION", "Description de ce tarif"), ("PERSO", "Un label personnalisé")]
    label_type = forms.TypedChoiceField(label="Label de la prestation", choices=choix_label, initial='NOM_TARIF', required=False)

    class Meta:
        model = TarifProduit
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idproduit = kwargs.pop("idproduit", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'produits_tarifs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Label perso
        if self.instance.label_prestation in ("NOM_TARIF", "nom_tarif", None, ""):
            self.fields['label_type'].initial = "NOM_TARIF"
            self.fields['label_prestation'].initial = None
        elif self.instance.label_prestation in ("DESCRIPTION", "description_tarif"):
            self.fields['label_type'].initial = "DESCRIPTION"
            self.fields['label_prestation'].initial = None
        else:
            self.fields['label_type'].initial = "PERSO"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden("produit", value=idproduit),
            TabHolder(
                Tab("Généralités",
                    Field("date_debut"),
                    Field("date_fin"),
                    Field("description"),
                    Field("observations"),
                    Fieldset("Label de la prestation",
                        Field("label_type"),
                        Field("label_prestation"),
                    ),
                    Field("code_compta"),
                    PrependedText('tva', '%'),
                ),
                Tab("Calcul du tarif",
                    Field("methode"),
                    Field("montant"),
                ),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Label de la prestation
        if self.cleaned_data["label_type"] == "PERSO":
            if self.cleaned_data["label_prestation"] == None:
                self.add_error('label_prestation', "Vous devez saisir un label de prestation personnalisé")
                return
        elif self.cleaned_data["label_type"] == "DESCRIPTION":
            if self.cleaned_data["description"]== None:
                self.add_error('description', "Vous devez saisir une description qui sera utilisée en tant que label de prestation")
                return
            self.cleaned_data["label_prestation"] = "description_tarif"
        else:
            self.cleaned_data["label_prestation"] = "nom_tarif"

        return self.cleaned_data


EXTRA_SCRIPT = """
{{ form.errors }}
{% if form.errors %}
    {% for field in form %}
        {% for error in field.errors %}
            <p> {{ error }} </p>
        {% endfor %}
    {% endfor %}
{% endif %}

<script>

// label_type
function On_change_label_type() {
    $('#div_id_label_prestation').hide();
    if($(this).val() == 'PERSO') {
        $('#div_id_label_prestation').show();
    }
}
$(document).ready(function() {
    $('#id_label_type').change(On_change_label_type);
    On_change_label_type.call($('#id_label_type').get(0));
});

</script>
"""
