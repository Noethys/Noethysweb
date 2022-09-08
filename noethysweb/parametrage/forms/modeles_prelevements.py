# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import PrelevementsModele, CHOIX_FORMAT_PRELEVEMENTS


class Formulaire_creation(FormulaireBase, forms.Form):
    format = forms.ChoiceField(label="Format", choices=CHOIX_FORMAT_PRELEVEMENTS, required=True)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Recherche le dernier format utilisé
        lot = PrelevementsModele.objects.last()
        if lot:
            self.fields["format"].initial = lot.format

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection du format",
                Field("format"),
            ),
        )


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = PrelevementsModele
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        format = kwargs.pop("format", None)
        if kwargs.get("instance", None):
            format = kwargs["instance"].format
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_prelevements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Format
        self.fields["format"].disabled = True
        if not self.instance.pk:
            self.fields["format"].initial = format

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_prelevements_liste' %}"),
            Fieldset("Généralités",
                Field("format"),
                Field("nom"),
                Field("observations"),
            ),
            Fieldset("Paramètres",
                Field("compte"),
                Field("perception", type=None if format in ("public_dft",) else "hidden"),
                Field("identifiant_service", type=None if format in ("public_dft",) else "hidden"),
                Field("poste_comptable", type=None if format in ("public_dft",) else "hidden"),
                Field("encodage"),
            ),
            Fieldset("Règlement automatique",
                Field("reglement_auto"),
                Field("mode"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        format = self.cleaned_data["format"]

        if not self.cleaned_data["perception"] and format in ("public_dft",):
            self.add_error("perception", "Vous devez sélectionner une perception")

        if not self.cleaned_data["identifiant_service"] and format in ("public_dft",):
            self.add_error("identifiant_service", "Vous devez renseigner l'identifiant du service")

        if not self.cleaned_data["poste_comptable"] and format in ("public_dft",):
            self.add_error("poste_comptable", "Vous devez renseigner le codique DDFiP.")

        return self.cleaned_data

EXTRA_SCRIPT = """
<script>

// Règlement automatique
function On_change_reglement_auto() {
    $('#div_id_mode').hide();
    if ($(this).prop("checked")) {
        $('#div_id_mode').show();
    }
}
$(document).ready(function() {
    $('#id_reglement_auto').change(On_change_reglement_auto);
    On_change_reglement_auto.call($('#id_reglement_auto').get(0));
});

</script>
"""
