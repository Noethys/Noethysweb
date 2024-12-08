# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Groupe, Activite
from django.db.models import Max


class Formulaire(FormulaireBase, ModelForm):
    # Nombre max d'inscrits
    choix_nbre_inscrits = [("NON", "Sans limitation du nombre d'inscrits"), ("OUI", "Avec limitation du nombre d'inscrits")]
    type_nbre_inscrits = forms.TypedChoiceField(label="Limitation du nombre d'inscrits", choices=choix_nbre_inscrits, initial="NON", required=True, help_text="""
                                                Vous pouvez ici définir le nombre d'inscrits maximal autorisé sur ce groupe. Attention, il ne s'agit pas ici du nombre de places
                                                maximales par jour (qui se paramètre dans le calendrier), mais bien du nombre d'inscriptions initiales. Cette option n'est 
                                                généralement utilisée que pour des activités limitées dans le temps. Exemples : Club de gym - Saison 2024-25, 
                                                Séjour à la neige - février 2026...""")

    class Meta:
        model = Groupe
        fields = "__all__"
        help_texts = {
            "nom": "Exemples : 3-6 ans, 6-12 ans, Les séniors, Les bébés, Le groupe du jeudi soir...",
            "abrege": "Il doit s'agir de quelques caractères en majuscules ou de chiffres. Exemples : 3-6, 6-12, SENIORS, JEUDI..."
        }

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_groupes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "activite") == False:
            activite = Activite.objects.get(pk=idactivite)
        else:
            activite = self.instance.activite

        # Ordre
        if self.instance.ordre == None:
            max = Groupe.objects.filter(activite=activite).aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Importe la limitation du nombre d'inscrits
        if self.instance.nbre_inscrits_max == None :
            self.fields['type_nbre_inscrits'].initial = "NON"
        else:
            self.fields['type_nbre_inscrits'].initial = "OUI"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=activite.idactivite),
            Hidden('ordre', value=self.fields['ordre'].initial),
            Fieldset("Nom du groupe",
                Field("nom"),
                Field("abrege"),
            ),
            Fieldset("Limitation du nombre d'inscrits",
                Field("type_nbre_inscrits"),
                Field("nbre_inscrits_max"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Limitation du nombre d'inscrits
        if self.cleaned_data["type_nbre_inscrits"] == "OUI":
            if self.cleaned_data["nbre_inscrits_max"] in (None, 0):
                self.add_error('nbre_inscrits_max', "Vous devez saisir une valeur")
                return
        else:
            self.cleaned_data["nbre_inscrits_max"] = None

        return self.cleaned_data



EXTRA_SCRIPT = """
<script>

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

</script>
"""