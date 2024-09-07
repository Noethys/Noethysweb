# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Scolarite, Individu, Ecole, Classe
from core.widgets import DatePickerWidget
from django_select2.forms import ModelSelect2Widget, Select2Widget


class Formulaire(FormulaireBase, ModelForm):
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=True, widget=DatePickerWidget())

    class Meta:
        model = Scolarite
        fields = "__all__"
        widgets = {
            "ecole": Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
            "classe": Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
            "niveau": Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
        }

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu", None)
        idclasse = kwargs.pop("idclasse", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_scolarite_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Individu
        if not idindividu:
            self.fields["individu"] = forms.ModelChoiceField(label="Individu", widget=ModelSelect2Widget(model=Individu, search_fields=['nom__icontains', 'prenom__icontains'], attrs={"lang": "fr", "data-width": "100%"}), queryset=Individu.objects.all().order_by("nom", "prenom"), required=True)

        # Ecole
        self.fields["ecole"].queryset = Ecole.objects.all().order_by("nom")

        # Définit l'individu associé
        if hasattr(self.instance, "individu") == False:
            if idindividu:
                individu = Individu.objects.get(pk=idindividu)
        else:
            individu = self.instance.individu

        # Récupération de l'école et des dates de la dernière classe saisie
        if self.instance.date_debut == None:
            classe = Scolarite.objects.last()
            if classe != None:
                self.fields["date_debut"].initial = classe.date_debut
                self.fields["date_fin"].initial = classe.date_fin

            # On récupère la dernière école de l'individu
            if idindividu and not idclasse:
                derniere_classe_individu = Scolarite.objects.filter(individu_id=idindividu).last()
                if derniere_classe_individu:
                    self.fields["ecole"].initial = derniere_classe_individu.ecole

        # Si on vient de la gestion des inscriptions scolaires, on définit la classe par défaut
        if idclasse:
            classe = Classe.objects.get(pk=idclasse)
            self.fields["date_debut"].initial = classe.date_debut
            self.fields["date_fin"].initial = classe.date_fin
            self.fields["ecole"].initial = classe.ecole
            self.fields["ecole"].disabled = True
            self.fields["classe"].initial = classe
            self.fields["classe"].disabled = True
            if classe.niveaux.count() == 1:
                self.fields["niveau"].initial = classe.niveaux.first()
                self.fields["niveau"].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('individu', value=individu.idindividu) if idindividu else Field("individu"),
            Field('date_debut'),
            Field('date_fin'),
            Field('ecole'),
            Field('classe'),
            Field("niveau"),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Période d'application
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"] :
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Actualise la liste des classes en fonction des dates et de l'école sélectionnée
function On_change_ecole() {
    var date_debut = $("#id_date_debut").val();
    var date_fin = $("#id_date_fin").val();
    var idecole = $("#id_ecole").val();
    var idclasse = $("#id_classe").val();
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_get_classes' %}",
        data: {'idecole': idecole, 'date_debut': date_debut, 'date_fin': date_fin},
        success: function (data) { 
            $("#id_classe").html(data); 
            $("#id_classe").val(idclasse);
            On_change_classe();
            if (data == '') {
                $("#div_id_classe").hide()
            } else {
                $("#div_id_classe").show()
            }
        }
    });
};
$(document).ready(function() {
    $('#id_ecole').change(On_change_ecole);
    On_change_ecole.call($('#id_ecole').get(0));
});


// On changement période
$(document).ready(function() {
    $('.datepickerwidget').on('change', function (e) {   
        On_change_ecole();
    });
});

// Actualise la liste des niveaux en fonction de la classe sélectionnée
function On_change_classe() {
    var idclasse = $("#id_classe").val(); 
    var idniveau = $("#id_niveau").val(); 
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_get_niveaux' %}",
        data: {'idclasse': idclasse},
        success: function (data) { 
            $("#id_niveau").html(data); 
            $("#id_niveau").val(idniveau);
            if (data == '') {
                $("#div_id_niveau").hide()
            } else {
                $("#div_id_niveau").show()
            }
        }
    });
};
$(document).ready(function() {
    $('#id_classe').change(On_change_classe);
    On_change_classe.call($('#id_classe').get(0));
});


</script>

"""