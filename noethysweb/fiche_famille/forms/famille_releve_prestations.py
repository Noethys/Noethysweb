# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Hidden
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.forms.base import FormulaireBase
from core.widgets import DateRangePickerWidget
from core.utils import utils_dates, utils_parametres
from fiche_famille.widgets import Periodes_releve_prestations


class Formulaire(FormulaireBase, forms.Form):
    periodes = forms.CharField(label="Périodes", required=True, widget=Periodes_releve_prestations(attrs={}))
    memoriser = forms.BooleanField(label="Mémoriser les périodes", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Récupération des paramètres mémorisés
        parametres = utils_parametres.Get_categorie(categorie="releve_prestations", utilisateur=self.request.user, parametres={"periodes": []})

        # Ventilation
        self.fields["periodes"].widget.request = self.request
        self.fields["periodes"].initial = json.dumps(parametres.get("periodes", []))

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_outils' idfamille=idfamille %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""<a type='button' class='btn btn-primary' title="Aperçu PDF" href='#' onclick="impression_pdf(false, true)"><i class="fa fa-file-pdf-o margin-r-5"></i>Aperçu PDF</a> """),
                    HTML("""<a type='button' class='btn btn-primary' title="Envoyer par Email" onclick="impression_pdf(true, false)" href='#'><i class="fa fa-send-o margin-r-5"></i>Envoyer par email</a> """),
                ],
            ),
            Fieldset("Périodes",
                Field("periodes"),
            ),
            Fieldset("Options",
                Field("memoriser"),
            ),
            Hidden("idfamille", value=idfamille),
        )


class Formulaire_periode(FormulaireBase, forms.Form):
    index = forms.CharField(widget=forms.HiddenInput(), required=False)
    type_donnee = forms.ChoiceField(label="Type", choices=[("PRESTATIONS", "Prestations"), ("FACTURES", "Factures")], required=True)
    type_periode = forms.ChoiceField(label="Période", choices=[("TOUTES", "Toutes les périodes"), ("SELECTION", "Uniquement la période sélectionnée")], required=True)
    periode = forms.CharField(label="Période", required=False, widget=DateRangePickerWidget())
    impayes = forms.BooleanField(label="Uniquement les impayés", required=False, initial=False)
    detail_conso = forms.BooleanField(label="Détailler les consommations", required=False, initial=False)
    regroupement = forms.ChoiceField(label="Regroupement", choices=[("DATE", "Date"), ("MOIS", "Mois"), ("ANNEE", "Année")], initial="DATE", required=False)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(Formulaire_periode, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "periode_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Field("index"),
            Fieldset("Généralités",
                Field("type_donnee"),
                Field("type_periode"),
                Field("periode"),
            ),
            Fieldset("Options",
                Field("impayes"),
                Field("detail_conso"),
                Field("regroupement")
            ),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        # Création du label pour l'affichage dans le tableau
        if self.cleaned_data["type_periode"] == "TOUTES":
            label = "Toutes les %s" % self.cleaned_data["type_donnee"].lower()
        else:
            date_debut, date_fin = utils_dates.ConvertDateRangePicker(self.cleaned_data["periode"])
            label = "Les %s du %s au %s" % (self.cleaned_data["type_donnee"].lower(), date_debut.strftime("%d/%m/%Y"), date_fin.strftime("%d/%m/%Y"))

        options = []
        if self.cleaned_data["impayes"]: options.append("uniquement les impayés")
        if self.cleaned_data["type_donnee"] == "PRESTATIONS":
            if self.cleaned_data["detail_conso"]: options.append("consommations détaillées")
            if self.cleaned_data["regroupement"] != "AUCUN": options.append("regroupement par %s" % self.cleaned_data["regroupement"].lower())
        if options: label += " (%s)" % ", ".join(options).capitalize()
        self.cleaned_data["label"] = label

        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_type_donnee() {
        $('#div_id_detail_conso').hide();
        $('#div_id_regroupement').hide();
        if ($("#id_type_donnee").val() == 'PRESTATIONS') {
            $('#div_id_detail_conso').show();
            $('#div_id_regroupement').show();
        };
    }
    $(document).ready(function() {
        $('#id_type_donnee').on('change', On_change_type_donnee);
        On_change_type_donnee.call($('#id_type_donnee').get(0));
    });

    function On_change_type_periode() {
        $('#div_id_periode').hide();
        if ($("#id_type_periode").val() == 'SELECTION') {
            $('#div_id_periode').show();
        };
    }
    $(document).ready(function() {
        $('#id_type_periode').on('change', On_change_type_periode);
        On_change_type_periode.call($('#id_type_periode').get(0));
    });
</script>
"""
