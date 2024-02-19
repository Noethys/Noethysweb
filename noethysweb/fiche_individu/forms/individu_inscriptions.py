# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Div, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Inscription, Individu, Activite, Consommation, QuestionnaireQuestion, QuestionnaireReponse
from core.widgets import DatePickerWidget
from core.forms.select2 import Select2Widget
from parametrage.forms import questionnaires


class Formulaire(FormulaireBase, ModelForm):
    activite = forms.ModelChoiceField(label="Activité", widget=Select2Widget(), queryset=Activite.objects.none(), required=True)
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget(), help_text="Laissez vide la date de fin si vous ne connaissez pas la durée de l'inscription.")
    action_conso = forms.ChoiceField(label="Action", required=False, choices=[
        (None, "------"),
        ("MODIFIER_TOUT", "Modifier toutes les consommations existantes"),
        ("MODIFIER_AUJOURDHUI", "Modifier les consommations existantes à partir d'aujourd'hui"),
        ("MODIFIER_DATE", "Modifier les consommations existantes à partir d'une date donnée"),
        ("MODIFIER_RIEN", "Ne pas modifier les consommations existantes"),
    ])
    date_modification = forms.DateField(label="Date", required=False, widget=DatePickerWidget(), help_text="Renseignez la date de début d'application de la modification.")

    class Meta:
        model = Inscription
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu", None)
        idfamille = kwargs.pop("idfamille", None)
        idactivite = kwargs.pop("idactivite", None)
        idgroupe = kwargs.pop("idgroupe", None)
        idcategorie_tarif = kwargs.pop("idcategorie_tarif", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_inscriptions_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'individu associé
        if hasattr(self.instance, "individu") == False:
            individu = Individu.objects.get(pk=idindividu)
        else:
            individu = self.instance.individu

        # Liste les activités liées à la structure actuelle
        self.fields['activite'].queryset = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom")

        # Si c'est un ajout avec présélection de l'activité et du groupe
        # (utilisé surtout pour les demandes d'inscription depuis le portail)
        if idactivite:
            self.fields["activite"].initial = idactivite
        if idgroupe:
            self.fields["groupe"].initial = idgroupe
        if idcategorie_tarif:
            self.fields["categorie_tarif"].initial = idcategorie_tarif

        # Si modification
        nbre_conso = 0
        if self.instance.idinscription != None:
            self.fields['individu'].disabled = True
            self.fields['famille'].disabled = True
            self.fields['activite'].disabled = True

            # Recherche si consommations existantes
            nbre_conso = Consommation.objects.filter(inscription=self.instance).count()
            if nbre_conso:
                self.fields["action_conso"].required = True
                self.fields["action_conso"].help_text = "Il existe déjà %d consommations associées à cette inscription. Que souhaitez-vous faire de ces consommations ?" % nbre_conso

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
                Field("internet_reservations"),
            ),
            HTML(EXTRA_SCRIPT),
        )

        # Affichage du champ consommations existantes
        if nbre_conso:
            self.helper.layout.insert(3,
                Fieldset("Consommations associées",
                    Div(
                        Field("action_conso"),
                        Field("date_modification"),
                        css_class="alert alert-warning"
                    ),
                ),
            )

        # Création des champs des questionnaires
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        questions = QuestionnaireQuestion.objects.filter(condition_structure, categorie="inscription", visible=True).order_by("ordre")
        if questions:
            liste_fields = []
            for question in questions:
                nom_controle, ctrl = questionnaires.Get_controle(question)
                if ctrl:
                    self.fields[nom_controle] = ctrl
                    liste_fields.append(Field(nom_controle))
            self.helper.layout.append(Fieldset("Questionnaire", *liste_fields))

            # Importation des réponses
            for reponse in QuestionnaireReponse.objects.filter(donnee=self.instance.pk, question__categorie="inscription"):
                key = "question_%d" % reponse.question_id
                if key in self.fields:
                    self.fields[key].initial = reponse.Get_reponse_for_ctrl()

    def clean(self):
        if self.cleaned_data["date_fin"] and self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return

        if self.cleaned_data["activite"].date_fin and self.cleaned_data["date_debut"] > self.cleaned_data["activite"].date_fin:
            self.add_error('date_debut', "La date de début doit être inférieure à la date de fin de l'activité")
            return

        # Questionnaires
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)

        return self.cleaned_data

    def save(self):
        instance = super(Formulaire, self).save()

        # Enregistrement des réponses du questionnaire
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                QuestionnaireReponse.objects.update_or_create(donnee=instance.pk, question_id=int(key.split("_")[1]), defaults={'reponse': valeur})

        return instance


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
            if ($("#id_groupe").children('option').length === 2) {
                $("#id_groupe").val($("#id_groupe option:eq(1)").val());
            };
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
            if ($("#id_categorie_tarif").children('option').length == 2) {
                $("#id_categorie_tarif").val($("#id_categorie_tarif option:eq(1)").val());
            };
        }
    });
};
$(document).ready(function() {
    $('#id_activite').change(On_change_activite);
    On_change_activite.call($('#id_activite').get(0));
});

// Affiche de la date de modification
function On_change_action() {
    $('#div_id_date_modification').hide();
    if ($("#id_action_conso").val() == 'MODIFIER_DATE') {
        $('#div_id_date_modification').show();
    };
}
$(document).ready(function() {
    $('#id_action_conso').on('change', On_change_action);
    On_change_action.call($('#id_action_conso').get(0));
});


</script>
"""