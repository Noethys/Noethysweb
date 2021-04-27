# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Inscription, Individu, Activite
from core.widgets import DatePickerWidget
from django_select2.forms import Select2Widget
import datetime



class Formulaire(ModelForm):
    activite = forms.ModelChoiceField(label="Activité", widget=Select2Widget({"lang": "fr"}), queryset=Activite.objects.all(), required=True)
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget(), help_text="Laissez vide la date de fin si vous ne connaissez pas la durée de l'inscription.")

    class Meta:
        model = Inscription
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu", None)
        idfamille = kwargs.pop("idfamille", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_inscriptions_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "individu") == False:
            individu = Individu.objects.get(pk=idindividu)
        else:
            individu = self.instance.individu

        # Si modification
        if self.instance.idinscription != None:
            self.fields['individu'].disabled = True
            self.fields['famille'].disabled = True
            self.fields['activite'].disabled = True

        # Période de validité
        if not self.instance.pk:
            self.fields['date_debut'].initial = datetime.date.today()

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('individu', value=individu.idindividu) if idindividu else Field("individu"),
            Hidden('famille', value=idfamille) if idfamille else Field("famille"),
            Fieldset("Période de validité",
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset("Activité",
                Field('activite'),
                Field('groupe'),
                Field('categorie_tarif'),
            ),
            Fieldset("Paramètres",
                Field("statut"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        if self.cleaned_data["date_fin"] and self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>


// Actualise la liste des groupes et des catégories de tarifs en fonction de l'activité sélectionnée
function On_change_activite() {
    var idactivite = $("#id_activite").val();
    var idgroupe = $("#id_groupe").val();
    var idcategorie_tarif = $("#id_categorie_tarif").val();
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_get_groupes' %}",
        data: {'idactivite': idactivite},
        success: function (data) { 
            $("#id_groupe").html(data); 
            $("#id_groupe").val(idgroupe);
            if (data == '') {
                $("#div_id_groupe").hide()
            } else {
                $("#div_id_groupe").show()
            }
        }
    });
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_get_categories_tarifs' %}",
        data: {'idactivite': idactivite},
        success: function (data) { 
            $("#id_categorie_tarif").html(data); 
            $("#id_categorie_tarif").val(idcategorie_tarif);
            if (data == '') {
                $("#div_id_categorie_tarif").hide()
            } else {
                $("#div_id_categorie_tarif").show()
            }
        }
    });
};
$(document).ready(function() {
    $('#id_activite').change(On_change_activite);
    On_change_activite.call($('#id_activite').get(0));
});


</script>
"""