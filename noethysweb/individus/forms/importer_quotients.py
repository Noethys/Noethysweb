# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Div
from crispy_forms.bootstrap import Field
from core.models import Quotient
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget, DateRangePickerWidget, SelectionActivitesWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    familles = forms.ChoiceField(label="Familles", choices=[("TOUTES", "Toutes les familles"), ("SELECTION", "Une sélection de familles")], initial="SELECTION", required=True, help_text="Généralement vous utiliserez l'option Une sélection de familles afin de cibler un panel de familles.")
    date = forms.DateField(label="Date de situation", required=True, widget=DatePickerWidget(), help_text="Sélectionnez la date à laquelle il faut rechercher l'existence ou l'absence d'un quotient.")
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"id": 2, "afficher_colonne_detail": False}), help_text="Cochez les activités ou les groupes d'activités auxquels l'individu doit être inscrit.")
    presents = forms.CharField(label="Uniquement les présents", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}), help_text="Cochez cette case pour sélectionner uniquement les individus ayant des consommations sur la période donnée.")
    filtre_quotients = forms.ChoiceField(label="Filtre", choices=[("TOUTES", "Familles avec ou sans QF"), ("AVEC_QF", "Uniquement les familles avec QF"), ("SANS_QF", "Uniquement les familles sans QF")], initial="SANS_QF", required=True, help_text="Vous choisirez généralement l'option Uniquement sans QF afin de cibler un panel de familles.")

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_importer_quotients"
        self.helper.form_method = "post"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        self.fields['date'].initial = datetime.date.today()

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'individus_toc' %}", enregistrer_label="<i class='fa fa-search margin-r-5'></i>Rechercher les quotients", ajouter=False),
            Field("familles"),
            Field("activites"),
            Field("presents"),
            Field("filtre_quotients"),
            Field("date"),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<script>
    function On_change_familles() {
        $('#div_id_activites').hide();
        $('#div_id_presents').hide();
        if ($("#id_familles").val() == "SELECTION") {
            $('#div_id_activites').show();
            $('#div_id_presents').show();
        };
    }
    $(document).ready(function() {
        $('#id_familles').change(On_change_familles);
        On_change_familles.call($('#id_familles').get(0));
    });
</script>
"""


class Formulaire_parametres_enregistrer(FormulaireBase, forms.Form):
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de début de validité.")
    date_fin = forms.DateField(label="Date de fin", required=True, widget=DatePickerWidget(), help_text="Saisissez la date de fin de validité.")

    def __init__(self, *args, **kwargs):
        super(Formulaire_parametres_enregistrer, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_quotients_enregistrer_form'
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Insertion des valeurs du précédent quotient saisi
        dernier_quotient = Quotient.objects.last()
        if dernier_quotient:
            self.fields["date_debut"].initial = dernier_quotient.date_debut
            self.fields["date_fin"].initial = dernier_quotient.date_fin

        # Affichage
        self.helper.layout = Layout(
            Div(
                Field("date_debut"),
                Field("date_fin"),
            ),
        )

    def clean(self):
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return
        return self.cleaned_data
