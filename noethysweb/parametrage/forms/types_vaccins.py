# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import TypeVaccin, TypeMaladie
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    types_maladies = forms.ModelMultipleChoiceField(label="Types de maladies associées", widget=Select2MultipleWidget(), queryset=TypeMaladie.objects.all())

    # Champs libres pour la durée de validité
    choix_validite = [("ILLIMITEE", "Validité illimitée"), ("DUREE", "Une durée")]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='ILLIMITEE', required=True)
    validite_jours = forms.IntegerField(label="Jours", required=False)
    validite_mois = forms.IntegerField(label="Mois", required=False)
    validite_annees = forms.IntegerField(label="Années", required=False)

    class Meta:
        model = TypeVaccin
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'types_vaccins_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Validité
        self.fields["validite_jours"].widget.attrs.update({"min": 0})
        self.fields["validite_mois"].widget.attrs.update({"min": 0})
        self.fields["validite_annees"].widget.attrs.update({"min": 0})

        # Importe la durée de validité dans les champs libres
        if self.instance.duree_validite == None:
            # Durée illimitée
            self.fields['validite_type'].initial = "ILLIMITEE"
        elif self.instance.duree_validite.startswith("j"):
            # Si validité par durée
            self.fields['validite_type'].initial = "DUREE"
            jours, mois, annees = self.instance.duree_validite.split("-")
            self.fields['validite_jours'].initial = int(jours[1:])
            self.fields['validite_mois'].initial = int(mois[1:])
            self.fields['validite_annees'].initial = int(annees[1:])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_vaccins_liste' %}"),
            Fieldset('Généralités',
                Field('nom'),
            ),
            Fieldset('Durée de validité',
                Field('validite_type'),
                Div(
                    Field('validite_annees'),
                    Field('validite_mois'),
                    Field('validite_jours'),
                    id='bloc_duree'
                ),
            ),
            HTML(EXTRA_SCRIPT),
            Fieldset('Maladies',
                Field('types_maladies'),
            ),
        )


    def clean(self):
        """ Convertit les champs de validité en un seul champ duree_validite """
        # Durée illimitée
        if self.cleaned_data["validite_type"] == "ILLIMITEE":
            self.cleaned_data["duree_validite"] = None

        # Validité par durée
        if self.cleaned_data["validite_type"] == "DUREE":
            jours = int(self.cleaned_data["validite_jours"] or 0)
            mois = int(self.cleaned_data["validite_mois"] or 0)
            annees = int(self.cleaned_data["validite_annees"] or 0)
            if jours == 0 and mois == 0 and annees == 0:
                self.add_error('validite_type', "Vous devez saisir une durée en jours et/ou mois et/ou années")
                return
            self.cleaned_data["duree_validite"] = "j%d-m%d-a%d" % (jours, mois, annees)

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// validite_type
function On_change_validite_type() {
    $('#bloc_duree').hide();

    if($(this).val() == 'DUREE') {
        $('#bloc_duree').show();
    }
}
$(document).ready(function() {
    $('#id_validite_type').change(On_change_validite_type);
    On_change_validite_type.call($('#id_validite_type').get(0));
});

</script>
"""