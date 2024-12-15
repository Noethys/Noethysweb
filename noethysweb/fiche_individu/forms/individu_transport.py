# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django_select2.forms import ModelSelect2MultipleWidget
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.utils.utils_commandes import Commandes
from core.utils.utils_texte import Creation_tout_cocher
from core.models import Transport, Unite, JOURS_SEMAINE
from core.widgets import DatePickerWidget


class Widget_unites(ModelSelect2MultipleWidget):
    search_fields = ["nom__icontains"]

    def label_from_instance(widget, instance):
        label = "%s - %s" % (instance.activite.nom, instance.nom)
        return label


class Formulaire(FormulaireBase, ModelForm):
    # Récurrence
    choix_recurrence = [("AUCUNE", "Aucune"), ("PERIODE", "Selon le planning suivant")]
    recurrence = forms.TypedChoiceField(label="Récurrence", choices=choix_recurrence, initial="AUCUNE", required=False)
    recurrence_date_debut = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    recurrence_date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    recurrence_feries = forms.BooleanField(label="Inclure les fériés", required=False)
    recurrence_jours_scolaires = forms.MultipleChoiceField(label="Jours scolaires", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("recurrence_jours_scolaires"))
    recurrence_jours_vacances = forms.MultipleChoiceField(label="Jours de vacances", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("recurrence_jours_vacances"))
    choix_frequence = [(1, "Toutes les semaines"), (2, "Une semaine sur deux"),
                        (3, "Une semaine sur trois"), (4, "Une semaine sur quatre"),
                        (5, "Les semaines paires"), (6, "Les semaines impaires")]
    recurrence_frequence_type = forms.TypedChoiceField(label="Fréquence", choices=choix_frequence, initial=1, required=False)

    class Meta:
        model = Transport
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
            "depart_date": DatePickerWidget(),
            "arrivee_date": DatePickerWidget(),
            "depart_heure": forms.TimeInput(attrs={'type': 'time'}),
            "arrivee_heure": forms.TimeInput(attrs={'type': 'time'}),
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
            "unites": Widget_unites({"lang": "fr", "data-minimum-input-length": 0, "data-width": "100%"}),
        }
        labels = {
            "depart_date": "Date",
            "arrivee_date": "Date",
            "depart_heure": "Heure",
            "arrivee_heure": "Heure",
        }

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu", None)
        mode = kwargs.get("mode", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'transports_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Individu
        if not idindividu and self.instance.pk:
            idindividu = self.instance.individu_id
            mode = self.instance.mode

        # Unités
        self.fields["unites"].queryset = Unite.objects.select_related("activite").filter(activite__inscription__individu_id=idindividu).order_by("activite__nom", "ordre")

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}", ajouter=False),
            Hidden("page", value="transport"),
            Hidden("individu", value=idindividu),
            Hidden("mode", value=mode),
            Fieldset("Généralités",
                Field("categorie"),
                Field("compagnie"),
                Field("numero"),
                Field("details"),
                Field("ligne"),
                Field("observations"),
            ),
            Fieldset("Départ",
                Field("depart_date", type="hidden" if mode == "PROG" else None),
                Field("depart_heure"),
                Field("depart_arret"),
                Field("depart_lieu"),
                Field("depart_localisation"),
            ),
            Fieldset("Arrivée",
                Field("arrivee_date", type="hidden" if mode == "PROG" else None),
                Field("arrivee_heure"),
                Field("arrivee_arret"),
                Field("arrivee_lieu"),
                Field("arrivee_localisation"),
            ),
        )

        if mode == "TRANSP" and not self.instance.pk:
            self.helper.layout.append(
                Fieldset("Récurrence",
                    Field("recurrence"),
                    Div(
                        Field("recurrence_date_debut"),
                        Field("recurrence_date_fin"),
                        InlineCheckboxes("recurrence_jours_scolaires"),
                        InlineCheckboxes("recurrence_jours_vacances"),
                        Field("recurrence_feries"),
                        Field("recurrence_frequence_type"),
                        id="div_periode_recurrente",
                    ),
                ),
            )

        if mode == "PROG":
            self.helper.layout.append(
                Fieldset("Programmation",
                    Field("actif"),
                    Field("date_debut"),
                    Field("date_fin"),
                    InlineCheckboxes("jours_scolaires"),
                    InlineCheckboxes("jours_vacances"),
                    Field("unites"),
                ),
            )

        self.helper.layout.append(HTML(EXTRA_SCRIPT))

    def clean(self):
        # Généralités
        if not self.cleaned_data["depart_heure"]:
            self.add_error("depart_heure", "Vous devez renseigner l'heure de départ")
            return
        if not self.cleaned_data["arrivee_heure"]:
            self.add_error("arrivee_heure", "Vous devez renseigner l'heure d'arrivée")
            return
        if self.cleaned_data["depart_heure"] > self.cleaned_data["arrivee_heure"]:
            self.add_error("arrivee_heure", "L'heure d'arrivée doit être supérieure à l'heure de départ")
            return

        # Transport unique
        if self.cleaned_data["recurrence"] == "AUCUNE":
            if not self.cleaned_data["depart_date"]:
                self.add_error("depart_date", "Vous devez renseigner la date de départ")
                return
            if not self.cleaned_data["arrivee_date"]:
                self.add_error("arrivee_date", "Vous devez renseigner la date d'arrivée")
                return

        # Récurrence
        if self.cleaned_data["recurrence"] == "PERIODE":
            for code, label in [("date_debut", "date de début"), ("date_fin", "date de fin")]:
                if not self.cleaned_data["recurrence_%s" % code]:
                    self.add_error("recurrence_%s" % code, "Vous devez sélectionner une %s" % label)
                    return

        # Mode
        if self.cleaned_data["mode"] == "PROG":
            if not self.cleaned_data["date_debut"]:
                self.add_error("date_debut", "Vous devez renseigner la date de début")
                return
            if not self.cleaned_data["date_fin"]:
                self.add_error("date_fin", "Vous devez renseigner la date de fin")
                return
            if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
                self.add_error("date_fin", "la date de fin doit être supérieure à l'heure de début")
                return

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Catégorie
function On_change_categorie() {
    $("#div_id_compagnie").hide();
    $("#div_id_numero").hide();
    $("#div_id_details").hide();
    $("#div_id_ligne").hide();
    $("#div_id_depart_arret").hide();
    $("#div_id_depart_lieu").hide();
    $("#div_id_depart_localisation").hide();
    $("#div_id_arrivee_arret").hide();
    $("#div_id_arrivee_lieu").hide();
    $("#div_id_arrivee_localisation").hide();
    
    if ($(this).val() == "avion") {
        $("#div_id_compagnie").show();
        $("#div_id_numero").show();
        $("#div_id_details").show();
        $("#div_id_depart_lieu").show();
        $("#div_id_arrivee_lieu").show();
        $("label[for=id_numero]").text("N° de vol");
        $("label[for=id_depart_lieu]").text("Aéroport");
        $("label[for=id_arrivee_lieu]").text("Aéroport");
        Maj_champ("compagnie");
        Maj_champ("depart_lieu");
        Maj_champ("arrivee_lieu");
    }
    
    if (($(this).val() == "bateau") || ($(this).val() == "train")) {
        $("#div_id_compagnie").show();
        $("#div_id_details").show();
        $("#div_id_depart_lieu").show();
        $("#div_id_arrivee_lieu").show();
        Maj_champ("compagnie");
        Maj_champ("depart_lieu");
        Maj_champ("arrivee_lieu");
        if ($(this).val() == "bateau") {
            $("label[for=id_depart_lieu]").text("Port");
            $("label[for=id_arrivee_lieu]").text("Port");
        }
        if ($(this).val() == "train") {
            $("label[for=id_depart_lieu]").text("Gare");
            $("label[for=id_arrivee_lieu]").text("Gare");
        }
    }

    if (($(this).val() == "bus") || ($(this).val() == "car") || ($(this).val() == "metro") || ($(this).val() == "navette") || ($(this).val() == "pedibus")) {
        $("#div_id_compagnie").show();
        $("#div_id_ligne").show();
        $("#div_id_depart_arret").show();
        $("#div_id_arrivee_arret").show();
        Maj_champ("compagnie");
        Maj_champ("ligne");
    }

    if (($(this).val() == "marche") || ($(this).val() == "voiture") || ($(this).val() == "velo")) {
        $("#div_id_depart_localisation").show();
        $("#div_id_arrivee_localisation").show();
    }

    if ($(this).val() == "taxi") {
        $("#div_id_compagnie").show();
        $("#div_id_depart_localisation").show();
        $("#div_id_arrivee_localisation").show();
        Maj_champ("compagnie");
    }

}
$(document).ready(function() {
    $('#id_categorie').change(On_change_categorie);
    On_change_categorie.call($('#id_categorie').get(0));
});

// Ligne
function On_change_ligne() {
    var selection = $("#id_depart_arret").val();
    Maj_champ("depart_arret");
    $("#id_depart_arret").val(selection);
    var selection = $("#id_arrivee_arret").val();
    Maj_champ("arrivee_arret");
    $("#id_arrivee_arret").val(selection);
}
$(document).ready(function() {
    $('#id_ligne').change(On_change_ligne);
    On_change_ligne.call($('#id_ligne').get(0));
});

function Maj_champ(champ) {
    var selection = $("#id_" + champ).val();
    $.ajax({ 
        type: "POST",
        url: "{% url 'ajax_get_info_transport' %}",
        data: {
            "categorie": $("#id_categorie").val(),
            "champ": champ,
            "ligne": $("#id_ligne").val(),
        },
        success: function (data) { 
            $("#id_" + champ).html(data);
            $("#id_" + champ).val(selection);
        }
    });
};

// Récurrence
function On_change_recurrence() {
    $('#div_periode_recurrente').hide();
    $('#div_id_depart_date').show();
    $('#div_id_arrivee_date').show();
    if ($("#id_recurrence").val() == 'PERIODE') {
        $('#div_periode_recurrente').show();
        $('#div_id_depart_date').hide();
        $('#div_id_arrivee_date').hide();
    };
}
$(document).ready(function() {
    $('#id_recurrence').on('change', On_change_recurrence);
    On_change_recurrence.call($('#id_recurrence').get(0));
});

</script>
"""
