# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, ButtonHolder, Div, Fieldset
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.utils.utils_commandes import Commandes
from core.utils.utils_texte import Creation_tout_cocher
from core.widgets import MonthPickerWidget, DatePickerWidget
from core.models import JOURS_SEMAINE
from core.forms.base import FormulaireBase
from parametrage.widgets import CalendrierOuvertures


class Formulaire(FormulaireBase, forms.Form):
    choix_mois = forms.DateField(label="Sélection du mois", required=False, widget=MonthPickerWidget())
    calendrier = forms.CharField(label="Calendrier des ouvertures", required=False, widget=CalendrierOuvertures())

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'form_calendrier_ouvertures'

        self.fields['choix_mois'].label = False
        self.fields['calendrier'].label = False

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'activites_calendrier' idactivite=idactivite %}", ajouter=False, autres_commandes=[
                HTML("""<a class="btn btn-default" data-toggle="modal" data-target="#modal_traitement_lot"><i class="fa fa-magic margin-r-5"></i> Saisie et suppression par lot</a> """),
            ]),
            Field('choix_mois'),
            HTML("<div id='in_progress' style='margin: 20px;text-align: center;'><i class='fa fa-2x fa-refresh fa-spin'></i> &nbsp;Chargement des données...</div>"),
            Div(
                Field('calendrier'),
                css_class="div_widget_calendrier"
            ),
        )


class Form_lot(forms.Form):
    # Action
    choix_action = [("COPIER_DATE", "Recopier une date"), ("REINIT", "Réinitialiser des dates")]
    action_type = forms.TypedChoiceField(label="Action à réaliser", choices=choix_action, initial='COPIER_DATE', required=False)
    date_modele = forms.DateField(label="Date à recopier", required=False, widget=DatePickerWidget())

    # Période d'application
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=True, widget=DatePickerWidget())
    inclure_feries = forms.BooleanField(label="Inclure les fériés", required=False)

    # Jours
    jours_scolaires = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_scolaires"))
    jours_vacances = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_vacances"))
    choix_frequence = [(1, "Toutes les semaines"), (2, "Une semaine sur deux"),
                        (3, "Une semaine sur trois"), (4, "Une semaine sur quatre"),
                        (5, "Les semaines paires"), (6, "Les semaines impaires")]
    frequence_type = forms.TypedChoiceField(label="Fréquence", choices=choix_frequence, initial=1, required=False)

    def __init__(self, *args, **kwargs):
        super(Form_lot, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        self.fields["jours_scolaires"].initial = [0, 1, 2, 3, 4]
        self.fields["jours_vacances"].initial = [0, 1, 2, 3, 4]

        self.helper.layout = Layout(
            Fieldset("Action",
                Field("action_type"),
                Field("date_modele"),
            ),
            Fieldset("Période d'application",
                Field("date_debut"),
                Field("date_fin"),
                Field("inclure_feries"),
            ),
            Fieldset("Jours",
                InlineCheckboxes("jours_scolaires"),
                InlineCheckboxes("jours_vacances"),
                Field("frequence_type"),
            ),
            ButtonHolder(
                Div(
                    Submit('submit', 'Valider', css_class='btn-primary'),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"
                ),
            ),
        )

    def clean(self):
        # Action
        if self.cleaned_data["action_type"] == "COPIER_DATE":
            if self.cleaned_data["date_modele"] == None:
                self.add_error("date_modele", 'Vous devez saisir une date à recopier')
                return

        # Période d'application
        if self.cleaned_data["date_debut"] == None:
            self.add_error('date_debut', "Vous devez sélectionner une date de début")
            return
        if self.cleaned_data["date_fin"] == None:
            self.add_error('date_fin', "Vous devez sélectionner une date de fin")
            return
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"] :
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return

        return self.cleaned_data
