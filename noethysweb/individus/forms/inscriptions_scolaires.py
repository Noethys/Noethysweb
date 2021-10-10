# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Ecole, Classe, NiveauScolaire
from django.db.models import Q, Count
from individus.widgets import SelectionElevesWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    ecole = forms.ModelChoiceField(label="Ecole", queryset=Ecole.objects.all(), required=False)
    periode = forms.ChoiceField(label="Période", choices=[], required=False)
    classe = forms.ModelChoiceField(label="Classe", queryset=Classe.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        idclasse = kwargs.pop("idclasse", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_inscriptions_scolaires'
        self.helper.form_method = 'post'

        periodes = [("%s_%s" % (periode["date_debut"], periode["date_fin"]), "") for periode in Classe.objects.values("date_debut", "date_fin").all().annotate(nbre_classes=Count("pk"))]
        self.fields["periode"].choices = periodes

        if idclasse:
            classe = Classe.objects.get(pk=idclasse)
            self.fields["ecole"].initial = classe.ecole
            self.fields["periode"].initial = "%s_%s" % (classe.date_debut, classe.date_fin)
            self.fields["classe"].initial = classe

        self.helper.layout = Layout(
            Field('ecole'),
            Field('periode'),
            Field('classe'),
            HTML(EXTRA_SCRIPT),
        )


EXTRA_SCRIPT = """
<script>

{% include 'core/csrftoken.html' %}

// Actualise la liste des périodes en fonction de l'école sélectionnée
function On_change_ecole() {
    var idecole = $("#id_ecole").val();
    var periode = $("#id_periode").val();
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_inscriptions_scolaires_get_periodes' %}",
        data: {'idecole': idecole},
        success: function (data) { 
            $("#id_periode").html(data);
            $("#id_periode").val(periode); 
            On_change_periode();
            if (data == '') {
                $("#div_id_periode").hide()
            } else {
                $("#div_id_periode").show()
            }
        }
    });
};
$(document).ready(function() {
    $('#id_ecole').change(On_change_ecole);
    On_change_ecole.call($('#id_ecole').get(0));
});



// Actualise la liste des classes en fonction de la période sélectionnée
function On_change_periode() {
    var idecole = $("#id_ecole").val(); 
    var periode = $("#id_periode").val();
    var classe = $("#id_classe").val(); 
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_inscriptions_scolaires_get_classes' %}",
        data: {'idecole': idecole, 'periode': periode},
        success: function (data) { 
            $("#id_classe").html(data); 
            $("#id_classe").val(classe); 
            if (data == '') {
                $("#div_id_classe").hide()
            } else {
                $("#div_id_classe").show()
            }
        }
    });
};
$(document).ready(function() {
    $('#id_periode').change(On_change_periode);
    On_change_periode.call($('#id_periode').get(0));
});


// Actualise la liste des inscrits en fonction de la classe sélectionnée
function On_change_classe() {
    var idclasse = $("#id_classe").val(); 
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_inscriptions_scolaires_get_inscrits' %}",
        data: {'idclasse': idclasse},
        success: function (data) { 
            $("#table_id_inscrits").html(data); 
            if (data == '') {
                $("#div_id_inscrits").hide()
            } else {
                $("#div_id_inscrits").show()
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




class Formulaire_ajouter_plusieurs(FormulaireBase, forms.Form):
    niveau = forms.ModelChoiceField(label="Niveau", queryset=NiveauScolaire.objects.all().order_by("ordre"), required=True)
    ecole = forms.ModelChoiceField(label="Ecole", queryset=Ecole.objects.all(), required=True)
    periode = forms.ChoiceField(label="Période", choices=[], required=True)
    classe = forms.ModelChoiceField(label="Classe", queryset=Classe.objects.all(), required=True)
    inscrits = forms.CharField(label="Inscrits", required=False, widget=SelectionElevesWidget())
    idclasse = forms.IntegerField(label="idclasse")

    def __init__(self, *args, **kwargs):
        idclasse = kwargs.pop("idclasse", None)
        kwargs.pop("instance", None)
        super(Formulaire_ajouter_plusieurs, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'inscriptions_scolaires_ajouter_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        periodes = [("%s_%s" % (periode["date_debut"], periode["date_fin"]), "") for periode in Classe.objects.values("date_debut", "date_fin").all().annotate(nbre_classes=Count("pk"))]
        self.fields["periode"].choices = periodes

        # Importation des niveaux de la classe
        if idclasse:
            niveaux = Classe.objects.get(pk=idclasse).niveaux.all().order_by("ordre")
            self.fields["niveau"].queryset = niveaux
            if niveaux.count() == 1:
                self.fields["niveau"].initial = niveaux.first()

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'inscriptions_scolaires_liste' idclasse=idclasse %}"),
            Hidden('idclasse', value=idclasse),
            Fieldset("Paramètres de l'inscription",
                Field('niveau'),
            ),
            Fieldset('Sélection des individus à inscrire',
                Field('ecole'),
                Field('periode'),
                Field('classe'),
                Field('inscrits'),
            ),
            HTML(EXTRA_SCRIPT),
        )

