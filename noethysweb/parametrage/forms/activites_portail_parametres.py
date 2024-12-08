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
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.utils.utils_commandes import Commandes
from core.models import Activite, ModeleEmail, JOURS_SEMAINE, JOURS_COMPLETS_SEMAINE
from core.widgets import DateTimePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    portail_inscriptions_date_debut = forms.DateTimeField(label="Date de début*", required=False, widget=DateTimePickerWidget())
    portail_inscriptions_date_fin = forms.DateTimeField(label="Date de fin*", required=False, widget=DateTimePickerWidget())

    # Limite de modification
    liste_choix = [(None, "Aucun"),]
    liste_choix.extend([(1000 + num_jour, "%s précédent" % label_jour) for num_jour, label_jour in JOURS_COMPLETS_SEMAINE])
    liste_choix.extend([(2000 + num_jour, "%s de la semaine précédente" % label_jour) for num_jour, label_jour in JOURS_COMPLETS_SEMAINE])
    liste_choix.extend([(3000 + num_jour, "%s de la semaine S-2" % label_jour) for num_jour, label_jour in JOURS_COMPLETS_SEMAINE])
    liste_choix.append((0, "Jour J"))
    for x in range(1, 31):
        liste_choix.append((x, "Jour J-%d" % x))
    liste_choix.append((60, "Jour J-60"))
    liste_choix.append((90, "Jour J-90"))
    liste_choix.append((120, "Jour J-120"))
    liste_choix.append((150, "Jour J-150"))
    liste_choix.append((180, "Jour J-180"))
    liste_choix.append((365, "Jour J-365"))
    limite_delai = forms.TypedChoiceField(label="Délai de modification", choices=liste_choix, initial=None, required=False, help_text="Une réservation peut être ajoutée, modifiée ou supprimée jusqu'à...")
    limite_heure = forms.TimeField(label="Heure limite", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    exclure_weekends = forms.BooleanField(label="Exclure les weeks-ends", required=False, initial=False)
    exclure_feries = forms.BooleanField(label="Exclure les jours fériés", required=False, initial=False)
    exclure_jours = forms.MultipleChoiceField(label="Exclure les jours", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE)

    class Meta:
        model = Activite
        fields = ["portail_inscriptions_affichage", "portail_inscriptions_date_debut", "portail_inscriptions_date_fin", "portail_reservations_affichage",
                  "portail_reservations_limite", "portail_afficher_dates_passees", "portail_inscriptions_bloquer_si_complet", "portail_inscriptions_imposer_pieces",
                  "reattribution_auto", "reattribution_adresse_exp", "reattribution_delai", "reattribution_modele_email",
                  "validation_type", "validation_modele_email",
                  ]
        help_texts = {
            "portail_inscriptions_affichage": "Sélectionnez Autoriser pour permettre aux usagers de demander une inscription à cette activité depuis le portail. Cette demande devra être validée par un utilisateur.",
            "portail_reservations_affichage": "Sélectionnez Autoriser pour permettre aux usagers de gérer leurs réservations pour cette activité sur le portail.",
            "portail_inscriptions_bloquer_si_complet": "L'usager ne peut pas envoyer sa demande d'inscription si l'activité est complète.",
            "portail_inscriptions_imposer_pieces": "Cochez cette case si vous souhaitez que l'usager fournisse obligatoirement les pièces manquantes depuis le portail pour valider sa demande d'inscription.",
            "portail_afficher_dates_passees": "Vous pouvez sélectionner la période passée que l'usager pourra visualiser dans le planning des réservations sur le portail. Ces dates passées seront bien-sûr uniquement en mode lecture.",
            "reattribution_adresse_exp": "Sélectionnez l'adresse d'expédition d'emails qui sera utilisée pour envoyer des notifications par email aux familles (Réattributions de places ou validations manuelles de réservations).",
            "reattribution_modele_email": "Sélectionnez le modèle d'email qui sera utilisé pour notifier les familles par email de la réattribution. Si aucun modèle n'est disponible, vous devez le créer dans le menu Paramétrage > Modèles d'emails > Catégorie = Attribution de places disponibles. N'oubliez pas de sélectionner également au bas de cette page l'adresse d'expédition souhaitée.",
            "validation_type": "Sélectionnez Automatique pour que la réservation soit instantanée ou Manuelle pour effectuer vous-même la validation manuelle de chaque réservation.",
            "validation_modele_email": "Sélectionnez le modèle d'email qui sera utilisé pour notifier les familles par email du traitement de la demande. Uniquement utile si la validation des réservations est manuelle. Si aucun modèle n'est disponible, vous devez le créer dans le menu Paramétrage > Modèles d'emails > Catégorie = Demande d'une réservation. N'oubliez pas de sélectionner également au bas de cette page l'adresse d'expédition souhaitée.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_portail_parametres_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3 col-form-label'
        self.helper.field_class = 'col-md-9'

        # Limite
        if self.instance.portail_reservations_limite:
            parametres_limite = self.instance.portail_reservations_limite.split("#")
            self.fields["limite_delai"].initial = int(parametres_limite[0])
            self.fields["limite_heure"].initial = datetime.datetime.strptime(parametres_limite[1], '%H:%M')
            self.fields["exclure_weekends"].initial = "exclure_weekends" in self.instance.portail_reservations_limite
            self.fields["exclure_feries"].initial = "exclure_feries" in self.instance.portail_reservations_limite
            if "exclure_jours" in self.instance.portail_reservations_limite:
                for chaine in self.instance.portail_reservations_limite.split("#"):
                    if "exclure_jours" in chaine:
                        self.fields["exclure_jours"].initial = [int(num_jour) for num_jour in chaine.replace("exclure_jours", "")]

        # Modèle d'email de validation
        self.fields["validation_modele_email"].queryset = ModeleEmail.objects.filter(categorie="portail_demande_reservation")

        # Modèle d'email de réattribution
        self.fields["reattribution_modele_email"].queryset = ModeleEmail.objects.filter(categorie="portail_places_disponibles")

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
                Field("portail_inscriptions_bloquer_si_complet"),
                Field("portail_inscriptions_imposer_pieces"),
            ),
            Fieldset("Réservations",
                Field("portail_reservations_affichage"),
                Field("limite_delai"),
                Div(
                    Field("limite_heure"),
                    Field("exclure_weekends"),
                    Field("exclure_feries"),
                    InlineCheckboxes("exclure_jours"),
                    id="bloc_limite"
                ),
                Field("portail_afficher_dates_passees"),
                ),
            Fieldset("Validation des réservations",
                Field("validation_type"),
                Field("validation_modele_email"),
            ),
            Fieldset("Réattribution automatique des places en attente",
                Field("reattribution_auto"),
                Field("reattribution_delai"),
                Field("reattribution_modele_email"),
            ),
            Fieldset("Expédition d'emails",
                Field("reattribution_adresse_exp"),
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
            if self.cleaned_data["exclure_jours"]: parametres_limite.append("exclure_jours%s" % "".join(str(num_jour) for num_jour in self.cleaned_data["exclure_jours"]))
            self.cleaned_data["portail_reservations_limite"] = "#".join(parametres_limite)
        else:
            self.cleaned_data["portail_reservations_limite"] = None

        # Réattribution de places disponibles
        if self.cleaned_data["reattribution_auto"]:
            if not self.cleaned_data["reattribution_adresse_exp"]:
                self.add_error("reattribution_adresse_exp", "Vous devez sélectionner une adresse d'expédition d'emails")
                return
            if not self.cleaned_data["reattribution_modele_email"]:
                self.add_error("reattribution_modele_email", "Vous devez sélectionner un modèle d'emails")
                return

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
