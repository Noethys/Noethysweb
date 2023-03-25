# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Activite
from core.widgets import DateTimePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    portail_inscriptions_date_debut = forms.DateTimeField(label="Date de début*", required=False, widget=DateTimePickerWidget())
    portail_inscriptions_date_fin = forms.DateTimeField(label="Date de fin*", required=False, widget=DateTimePickerWidget())

    # Limite de modification
    liste_choix = [(None, "Aucun"),
        (1000, "Lundi précédent"), (1001, "Mardi précédent"),
        (1002, "Mercredi précédent"), (1003, "Jeudi précédent"), (1004, "Vendredi précédent"),
        (1005, "Samedi précédent"), (1006, "Dimanche précédent"), (2000, "Lundi de la semaine précédente"),
        (2001, "Mardi de la semaine précédente"), (2002, "Mercredi de la semaine précédente"),
        (2003, "Jeudi de la semaine précédente"), (2004, "Vendredi de la semaine précédente"),
        (2005, "Samedi de la semaine précédente"), (2006, "Dimanche de la semaine précédente"),
        (0, "Jour J"), ]
    for x in range(1, 31):
        liste_choix.append((x, "Jour J-%d" % x))
    limite_delai = forms.TypedChoiceField(label="Délai de modification", choices=liste_choix, initial=None, required=False, help_text="Une réservation peut être ajoutée, modifiée ou supprimée jusqu'à...")
    limite_heure = forms.TimeField(label="Heure limite", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    exclure_weekends = forms.BooleanField(label="Exclure les weeks-ends", required=False, initial=False)
    exclure_feries = forms.BooleanField(label="Exclure les jours fériés", required=False, initial=False)

    # Absence injustifiée
    # liste_choix = [(None, "Aucun"), (0, "Jour J")]
    # for x in range(1, 31):
    #     liste_choix.append((x, "Jour J-%d" % x))
    # absenti_delai = forms.TypedChoiceField(label="Délai de facturation", choices=liste_choix, initial=None, required=False, help_text="L'état Absence injustifiée est attribué aux réservations modifiées ou supprimées après...")
    # absenti_heure = forms.TimeField(label="Heure limite", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = Activite
        fields = ["portail_inscriptions_affichage", "portail_inscriptions_date_debut", "portail_inscriptions_date_fin", "portail_reservations_affichage",
                  "portail_reservations_limite", "portail_afficher_dates_passees", "portail_inscriptions_imposer_pieces",
                  # "portail_reservations_absenti", "portail_unites_multiples",
                  ]
        help_texts = {
            "portail_inscriptions_affichage": "Sélectionnez Autoriser pour permettre aux usagers de demander une inscription à cette activité depuis le portail. Cette demande devra être validée par un utilisateur.",
            "portail_reservations_affichage": "Sélectionnez Autoriser pour permettre aux usagers de gérer leurs réservations pour cette activité sur le portail.",
            "portail_inscriptions_imposer_pieces": "Cochez cette case si vous souhaitez que l'usager fournisse obligatoirement les pièces manquantes depuis le portail pour valider sa demande d'inscription.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_portail_parametres_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'

        # Limite
        if self.instance.portail_reservations_limite:
            parametres_limite = self.instance.portail_reservations_limite.split("#")
            self.fields["limite_delai"].initial = int(parametres_limite[0])
            self.fields["limite_heure"].initial = datetime.datetime.strptime(parametres_limite[1], '%H:%M')
            self.fields["exclure_weekends"].initial = "exclure_weekends" in self.instance.portail_reservations_limite
            self.fields["exclure_feries"].initial = "exclure_feries" in self.instance.portail_reservations_limite

        # Absenti
        # if self.instance.portail_reservations_absenti:
        #     parametres_absenti = self.instance.portail_reservations_absenti.split("#")
        #     self.fields["absenti_delai"].initial = int(parametres_absenti[0])
        #     self.fields["absenti_heure"].initial = datetime.datetime.strptime(parametres_absenti[1], '%H:%M')

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="activites_portail_parametres_modifier", modifier_args="idactivite=activite.idactivite", modifier=True, enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'activites_portail_parametres' idactivite=activite.idactivite %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Fieldset("Inscriptions",
                Field("portail_inscriptions_affichage"),
                Div(
                    Field("portail_inscriptions_date_debut"),
                    Field("portail_inscriptions_date_fin"),
                    id="bloc_inscriptions_periode"
                ),
                Field("portail_inscriptions_imposer_pieces"),
            ),
            Fieldset("Réservations",
                Field("portail_reservations_affichage"),
                Field("limite_delai"),
                Div(
                    Field("limite_heure"),
                    Field("exclure_weekends"),
                    Field("exclure_feries"),
                    id="bloc_limite"
                ),
                # Field("absenti_delai"),
                # Field("absenti_heure"),
                Field("portail_afficher_dates_passees"),
                # Field("portail_unites_multiples"),
                ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Inscriptions
        if self.cleaned_data["portail_inscriptions_affichage"] == "PERIODE":
            if not self.cleaned_data["portail_inscriptions_date_debut"]:
                self.add_error('portail_inscriptions_date_debut', "Vous devez sélectionner une date de début d'affichage")
                return
            if not self.cleaned_data["portail_inscriptions_date_fin"]:
                self.add_error('portail_inscriptions_date_fin', "Vous devez sélectionner une date de fin d'affichage")
                return
            if self.cleaned_data["portail_inscriptions_date_debut"] > self.cleaned_data["portail_inscriptions_date_fin"] :
                self.add_error('portail_inscriptions_date_fin', "La date de fin d'affichage doit être supérieure à la date de début")
                return
        else:
            self.cleaned_data["portail_inscriptions_date_debut"] = None
            self.cleaned_data["portail_inscriptions_date_fin"] = None

        # Limite
        if self.cleaned_data["limite_delai"]:
            if not self.cleaned_data["limite_heure"]:
                self.add_error('limite_heure', "Vous devez spécifier une heure limite")
                return
            parametres_limite = [self.cleaned_data["limite_delai"], self.cleaned_data["limite_heure"].strftime('%H:%M')]
            if self.cleaned_data["exclure_weekends"]: parametres_limite.append("exclure_weekends")
            if self.cleaned_data["exclure_feries"]: parametres_limite.append("exclure_feries")
            self.cleaned_data["portail_reservations_limite"] = "#".join(parametres_limite)
        else:
            self.cleaned_data["portail_reservations_limite"] = None

        # Absenti
        # if self.cleaned_data["absenti_delai"]:
        #     if not self.cleaned_data["absenti_heure"]:
        #         self.add_error('absenti_heure', "Vous devez spécifier une heure limite")
        #         return
        #     self.cleaned_data["portail_reservations_absenti"] = "#".join([self.cleaned_data["absenti_delai"], self.cleaned_data["absenti_heure"].strftime('%H:%M')])
        # else:
        #     self.cleaned_data["portail_reservations_absenti"] = None

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Inscriptions
function On_change_affichage_inscriptions() {
    $('#bloc_inscriptions_periode').hide();
    if($(this).val() == 'PERIODE') {
        $('#bloc_inscriptions_periode').show();
    }
}
$(document).ready(function() {
    $('#id_portail_inscriptions_affichage').change(On_change_affichage_inscriptions);
    On_change_affichage_inscriptions.call($('#id_portail_inscriptions_affichage').get(0));
});

// Heure limite
function On_change_limite_reservations() {
    $('#bloc_limite').hide();
    if($(this).val()) {
        $('#bloc_limite').show();
    }
}
$(document).ready(function() {
    $('#id_limite_delai').change(On_change_limite_reservations);
    On_change_limite_reservations.call($('#id_limite_delai').get(0));
});

// Absenti
function On_change_absenti_reservations() {
    $('#div_id_absenti_heure').hide();
    if($(this).val()) {
        $('#div_id_absenti_heure').show();
    }
}
$(document).ready(function() {
    $('#id_absenti_delai').change(On_change_absenti_reservations);
    On_change_absenti_reservations.call($('#id_absenti_delai').get(0));
});


</script>
"""
