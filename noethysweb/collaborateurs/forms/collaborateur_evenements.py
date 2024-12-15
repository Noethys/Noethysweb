# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from core.forms.select2 import Select2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils.utils_texte import Creation_tout_cocher
from core.models import EvenementCollaborateur, Collaborateur, JOURS_SEMAINE
from core.widgets import DatePickerWidget, DateTimePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    # Collaborateur
    collaborateur = forms.ModelChoiceField(label="Collaborateur", widget=Select2Widget({"data-minimum-input-length": 0}),
                                     queryset=Collaborateur.objects.all().order_by("nom", "prenom"), required=True)

    # Période
    choix_periode = [("UNIQUE", "Période unique"), ("RECURRENCE", "Récurrence")]
    selection_periode = forms.TypedChoiceField(label="Type de période", choices=choix_periode, initial="UNIQUE", required=False)
    recurrence_date_debut = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    recurrence_date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    recurrence_heure_debut = forms.TimeField(label="Heure de début", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    recurrence_heure_fin = forms.TimeField(label="Heure de fin", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    recurrence_feries = forms.BooleanField(label="Inclure les fériés", required=False)
    recurrence_jours_scolaires = forms.MultipleChoiceField(label="Jours scolaires", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("recurrence_jours_scolaires"))
    recurrence_jours_vacances = forms.MultipleChoiceField(label="Jours de vacances", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("recurrence_jours_vacances"))
    choix_frequence = [(1, "Toutes les semaines"), (2, "Une semaine sur deux"),
                        (3, "Une semaine sur trois"), (4, "Une semaine sur quatre"),
                        (5, "Les semaines paires"), (6, "Les semaines impaires")]
    recurrence_frequence_type = forms.TypedChoiceField(label="Fréquence", choices=choix_frequence, initial=1, required=False)

    class Meta:
        model = EvenementCollaborateur
        fields = "__all__"
        widgets = {
            "date_debut": DateTimePickerWidget(),
            "date_fin": DateTimePickerWidget(),
            "type_evenement": Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
        }
        help_texts = {
            "date_debut": "Saisissez une date et heure de début au format JJ/MM/AAAA HH:MM.",
            "date_fin": "Saisissez une date et heure de début au format JJ/MM/AAAA HH:MM.",
        }

    def __init__(self, *args, **kwargs):
        self.idcollaborateur = kwargs.pop("idcollaborateur", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'collaborateurs_evenements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        if self.idcollaborateur or self.instance.pk:
            self.fields["collaborateur"].initial = self.idcollaborateur
            self.fields["collaborateur"].widget.attrs["disabled"] = "disabled"
            self.fields["collaborateur"].disabled = True

        self.fields["date_debut"].required = True
        self.fields["type_evenement"].required = True

        self.fields["date_debut"].initial = datetime.datetime.now()
        self.fields["recurrence_jours_scolaires"].initial = [0, 1, 2, 3, 4]
        self.fields["recurrence_jours_vacances"].initial = [0, 1, 2, 3, 4]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('idevenement', value=self.instance.pk if self.instance else None),
            Fieldset("Généralités",
                Field("collaborateur"),
                Field("type_evenement"),
                Field("titre"),
            ),
            Fieldset("Période",
                Field("selection_periode"),
                Div(
                    Field("date_debut"),
                    Field("date_fin"),
                    id="div_periode_unique",
                ),
                Div(
                    Field("recurrence_date_debut"),
                    Field("recurrence_date_fin"),
                    Field("recurrence_feries"),
                    Field("recurrence_heure_debut"),
                    Field("recurrence_heure_fin"),
                    InlineCheckboxes("recurrence_jours_scolaires"),
                    InlineCheckboxes("recurrence_jours_vacances"),
                    Field("recurrence_frequence_type"),
                    id="div_periode_recurrente",
                ),
            ),
            HTML(EXTRA_SCRIPT),
        )

        # Intégration des commandes pour le mode planning
        if not self.idcollaborateur:
            commandes = Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False, autres_commandes=[
                HTML("""<button type="submit" name="enregistrer" title="Enregistrer" class="btn btn-primary"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """),
                HTML("""<a class="btn btn-danger" title="Annuler" onclick="$('#modal_detail_evenement').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """),
            ],)
            if self.instance.pk:
                commandes.insert(1, HTML("""<button type="button" class="btn btn-warning" onclick="supprimer_evenement(%d)"><i class="fa fa-trash margin-r-5"></i>Supprimer</button> """ % self.instance.pk))
            self.helper.layout[0] = commandes

    def clean(self):
        # Période
        if self.cleaned_data["selection_periode"] == "UNIQUE":
            if not self.cleaned_data["date_debut"]:
                self.add_error("date_debut", "Vous devez sélectionner une date de début")
                return
            if not self.cleaned_data["date_fin"]:
                self.add_error("date_fin", "Vous devez sélectionner une date de fin")
                return

        if self.cleaned_data["selection_periode"] == "RECURRENCE":
            for code, label in [("date_debut", "date de début"), ("date_fin", "date de fin"), ("heure_debut", "heure de début"), ("heure_fin", "heure de fin")]:
                if not self.cleaned_data["recurrence_%s" % code]:
                    self.add_error("recurrence_%s" % code, "Vous devez sélectionner une %s" % label)
                    return

        return self.cleaned_data


EXTRA_SCRIPT = """
{% load static %}

<script>

// Sélection période
function On_change_selection_periode() {
    $('#div_periode_unique').hide();
    $('#div_periode_recurrente').hide();
    if ($("#id_selection_periode").val() == 'UNIQUE') {
        $('#div_periode_unique').show();
    };
    if ($("#id_selection_periode").val() == 'RECURRENCE') {
        $('#div_periode_recurrente').show();
    };
}
$(document).ready(function() {
    $('#id_selection_periode').on('change', On_change_selection_periode);
    On_change_selection_periode.call($('#id_selection_periode').get(0));
});

</script>
"""
