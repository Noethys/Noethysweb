# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import re
from django import forms
from django.forms import ModelForm
from django_select2.forms import ModelSelect2Widget
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.utils.utils_commandes import Commandes
from core.utils.utils_texte import Creation_tout_cocher
from core.utils import utils_dates, utils_images
from core.models import Unite, Groupe, Activite, Evenement, Tarif, JOURS_SEMAINE
from core.widgets import DatePickerWidget, Crop_image


class Widget_copie_tarif_evenement(ModelSelect2Widget):
    search_fields = ["nom__icontains"]

    def label_from_instance(widget, instance):
        label = "%s : %s" % (utils_dates.ConvertDateToFR(instance.date), instance.nom)
        return label


class Formulaire(FormulaireBase, ModelForm):
    # Date
    mode_saisie = forms.TypedChoiceField(label="Mode de saisie", choices=[("UNIQUE", "Date unique"), ("MULTIDATES_SAISIE", "Dates multiples saisies dans le champ suivant"), ("MULTIDATES_CALENDRIER", "Dates multiples sélectionnées dans le calendrier suivant"),
                                                                          ("MULTIDATES_PLANNING", "Dates multiples selon le planning suivant")], initial="UNIQUE", required=False, help_text="Sélectionnez le mode Dates multiples si vous souhaitez dupliquer cet évènement sur plusieurs dates.")
    date = forms.DateField(label="Date", required=False, widget=DatePickerWidget(), help_text="Sélectionnez la date de l'évènement. Notez que l'application créera automatiquement une ouverture dans le calendrier des ouvertures lors de la création de cet événement.")
    multidates_saisie = forms.CharField(label="Dates", required=False, help_text="Saisissez les dates souhaitées séparées par des virgules ou des points-virgules. Exemple : 15/12/2023;16/12/2023;17/12/2023")
    multidates_calendrier = forms.CharField(label="Dates", required=False, widget=DatePickerWidget(attrs={"multidate": True, "affichage_inline": True}), help_text="Cochez les dates souhaitées dans le calendrier.")
    multidates_planning = forms.CharField(label="Dates", required=False)
    multidates_planning_date_debut = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget())
    multidates_planning_date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget())
    multidates_planning_inclure_feries = forms.BooleanField(label="Inclure les fériés", required=False)
    multidates_planning_jours_scolaires = forms.MultipleChoiceField(label="Jours scolaires", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("multidates_planning_jours_scolaires"))
    multidates_planning_jours_vacances = forms.MultipleChoiceField(label="Jours de vacances", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("multidates_planning_jours_vacances"))
    choix_frequence = [(1, "Toutes les semaines"), (2, "Une semaine sur deux"),
                        (3, "Une semaine sur trois"), (4, "Une semaine sur quatre"),
                        (5, "Les semaines paires"), (6, "Les semaines impaires")]
    multidates_planning_frequence_type = forms.TypedChoiceField(label="Fréquence", choices=choix_frequence, initial=1, required=False)

    # Généralités
    unite = forms.ModelChoiceField(label="Unité", queryset=Unite.objects.none(), required=True, help_text="Sélectionnez obligatoirement l'unité de consommation de type 'Evénementiel' associée à cet événement.")
    groupe = forms.ModelChoiceField(label="Groupe", queryset=Groupe.objects.none(), required=True, help_text="Sélectionnez obligatoirement le groupe associé à cet événement. Exemples : 10-14 ans, Les séniors, Groupe unique...")
    description = forms.CharField(label="Description", widget=forms.Textarea(attrs={'rows': 2}), required=False, help_text="""<i class='fa fa-exclamation-triangle'></i> 
                                    Cette description sera visible pour les familles sur le portail. C'est ici que vous pouvez par exemple indiquer les horaires de l'évènement
                                    ou le matériel à apporter. Exemples : RDV à 10h au port, n'oubliez pas vos casquettes...""")

    # Heures
    heure_debut = forms.TimeField(label="Heure de début", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Il est possible de renseigner ici une heure de début par défaut. Utile pour des statistiques par exemple.")
    heure_fin = forms.TimeField(label="Heure de fin", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Il est possible de renseigner ici une heure de fin par défaut. Utile pour des statistiques par exemple.")

    # Nombre max d'inscrits
    choix_nbre_places = [("NON", "Sans limitation du nombre de places"), ("OUI", "Avec limitation du nombre de places")]
    type_nbre_places = forms.TypedChoiceField(label="Places", choices=choix_nbre_places, initial="NON", required=False, help_text="""Il est possible de définir ici une
                                                capacité d'accueil maximale uniquement pour cet événement.""")
    capacite_max = forms.IntegerField(label="Nombre de places*", initial=0, min_value=0, required=False)

    # Tarification
    choix_tarification = [
        ("GRATUIT", "Gratuit"),
        ("SIMPLE", "Tarif simple"),
        ("AVANCE", "Tarification avancée"),
        ("EXISTANT", "Copie des tarifs d'un événement existant")
    ]
    texte_aide = "Pour créer, modifier ou supprimer des tarifs avancés, sélectionnez 'Tarification avancée', cliquez sur Enregistrer puis cliquez sur le bouton <i class='fa fa-gear'></i> sur la ligne de l'événement dans la liste des événements."
    type_tarification = forms.TypedChoiceField(label="Tarification", choices=choix_tarification, initial="GRATUIT", required=False, help_text=texte_aide)
    copie_evenement = forms.ModelChoiceField(label="Evénement", widget=Widget_copie_tarif_evenement({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}), queryset=Evenement.objects.none(), required=False)

    # Image
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Evenement
        fields = "__all__"
        widgets = {
            "equiv_heures": forms.TimeInput(attrs={'type': 'time'}),
            "image": Crop_image(attrs={"largeur_min": 400, "hauteur_min": 100, "ratio": "400/100"}),
        }
        help_texts = {
            "nom": "Saisissez un nom pour cet événement. Exemple : Patinoire, sortie familiale au zoo, Soirée karaoké, Atelier découverte de l'informatique...",
            "equiv_heures": "Saisissez l'équivalence en heures (utile uniquement pour l'état global et l'état nominatif). Format : HH:MM.",
            "image": "Vous pouvez sélectionner une image à appliquer sur l'arrière-plan de la case de l'évènement dans la grille des consommations. L'image sera convertie en niveaux de gris à l'affichage.",
            "categorie": "Vous pouvez associer ici une catégorie d'événements afin que cet événement hérite de ses caractéristiques.",
            "visible_portail": "Décochez cette case si vous souhaitez que les usagers ne puissent pas voir cet événement sur le planning des réservations du portail.",
        }

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_evenements_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "activite") == False:
            activite = Activite.objects.get(pk=idactivite)
        else:
            activite = self.instance.activite

        # Si modification
        if self.instance.pk:
            self.fields["date"].disabled = True
            self.fields["unite"].disabled = True
            self.fields["groupe"].disabled = True

        # Unité de consommation
        self.fields['unite'].queryset = Unite.objects.filter(activite=activite, type="Evenement").order_by("ordre")
        if not self.instance.pk and len(self.fields['unite'].queryset) == 1:
            # S'il n'y a qu'une seule unité de conso événementielle, on la sélectionne par défaut
            self.fields['unite'].initial = self.fields['unite'].queryset.first()

        # Groupe
        self.fields['groupe'].queryset = Groupe.objects.filter(activite=activite).order_by("ordre")
        if not self.instance.pk and len(self.fields['groupe'].queryset) == 1:
            # S'il n'y a qu'un groupe, on le sélectionne par défaut
            self.fields['groupe'].initial = self.fields['groupe'].queryset.first()

        # Jours
        self.fields["multidates_planning_jours_scolaires"].initial = [0, 1, 2, 3, 4]
        self.fields["multidates_planning_jours_vacances"].initial = [0, 1, 2, 3, 4]

        # Places max
        if self.instance.pk and self.instance.capacite_max:
            self.fields['type_nbre_places'].initial = "OUI"

        # Tarification
        if self.instance.pk:
            if self.instance.montant:
                self.fields['type_tarification'].initial = "SIMPLE"
            else:
                liste_tarifs = Tarif.objects.filter(evenement=self.instance)
                if len(liste_tarifs):
                    self.fields['type_tarification'].initial = "AVANCE"
                    self.fields['type_tarification'].disabled = True

        # Sélectionne les tarifs existants
        self.fields["copie_evenement"].queryset = Evenement.objects.filter(activite=activite).exclude(pk=self.instance.pk).order_by("-date")

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=activite.idactivite),
            Field("cropper_data"),
            Fieldset("Généralités",
                Field("nom"),
                Field("unite"),
                Field("groupe"),
            ),
            Fieldset("Date",
                Field("mode_saisie", type="hidden" if kwargs.get("instance", None) else None),
                Field("date"),
                Field("multidates_saisie", type="hidden" if kwargs.get("instance", None) else None),
                Field("multidates_calendrier", type="hidden" if kwargs.get("instance", None) else None),
                Div(
                    Field("multidates_planning", type="hidden"),
                    Field("multidates_planning_date_debut"),
                    Field("multidates_planning_date_fin"),
                    Field("multidates_planning_inclure_feries"),
                    InlineCheckboxes("multidates_planning_jours_scolaires"),
                    InlineCheckboxes("multidates_planning_jours_vacances"),
                    Field("multidates_planning_frequence_type"),
                    id="div_id_multidates_planning",
                )
            ),
            Fieldset("Options",
                Field("description"),
                Field("categorie"),
                Field("heure_debut"),
                Field("heure_fin"),
                Field("equiv_heures"),
                Field("visible_portail"),
            ),
            Fieldset("Limitation du nombre de places",
                Field("type_nbre_places"),
                Field("capacite_max"),
            ),
            Fieldset("Tarification",
                Field("type_tarification"),
                Field("montant"),
                Field("copie_evenement"),
            ),
            Fieldset("Image d'arrière-plan",
                Field("image"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Nbre de places
        if self.cleaned_data["type_nbre_places"] == "OUI" and self.cleaned_data["capacite_max"] == 0:
            self.add_error('capacite_max', "Vous devez saisir une capacité maximale")
            return

        # Tarification
        if self.cleaned_data["type_tarification"] == "SIMPLE" and self.cleaned_data["montant"] in (None, 0.0):
                self.add_error('montant', "Vous devez saisir un montant")
                return

        if self.cleaned_data["type_tarification"] in ("GRATUIT", "AVANCE"):
            self.cleaned_data["montant"] = None

        if self.cleaned_data["type_tarification"] == "EXISTANT" and not self.cleaned_data["copie_evenement"]:
                self.add_error('copie_evenement', "Vous devez sélectionner un événement existant dont les tarifs sont à dupliquer")
                return

        # Mode de saisie
        if self.cleaned_data["mode_saisie"] == "UNIQUE" and not self.cleaned_data["date"]:
            self.add_error("date", "Vous devez saisir une date pour cet évènement")
            return

        if self.cleaned_data["mode_saisie"] == "MULTIDATES_SAISIE":
            if not self.cleaned_data["multidates_saisie"]:
                self.add_error("multidates_saisie", "Vous devez saisir au mois une date pour cet évènement")
            liste_dates = []
            for datefr in re.split(';|,', self.cleaned_data["multidates_saisie"]):
                date = utils_dates.ConvertDateFRtoDate(datefr.strip())
                if date:
                    liste_dates.append(date)
                else:
                    self.add_error("multidates_saisie", "La date '%s' semble erronée" % datefr)
            self.cleaned_data["date"] = liste_dates[0]

        if self.cleaned_data["mode_saisie"] == "MULTIDATES_CALENDRIER":
            if not self.cleaned_data["multidates_calendrier"]:
                self.add_error("multidates_calendrier", "Vous devez saisir au mois une date pour cet évènement")
            liste_dates = []
            for dateeng in re.split(';|,', self.cleaned_data["multidates_calendrier"]):
                date = utils_dates.ConvertDateENGtoDate(dateeng)
                if date:
                    liste_dates.append(date)
                else:
                    self.add_error("multidates_calendrier", "La date '%s' semble erronée" % dateeng)
            self.cleaned_data["date"] = liste_dates[0]

        if self.cleaned_data["mode_saisie"] == "MULTIDATES_PLANNING":
            if not self.cleaned_data["multidates_planning_date_debut"]:
                self.add_error("multidates_planning_date_debut", "Vous devez sélectionner une date de début")
                return
            if not self.cleaned_data["multidates_planning_date_fin"]:
                self.add_error("multidates_planning_date_fin", "Vous devez sélectionner une date de fin")
                return
            if self.cleaned_data["multidates_planning_date_debut"] > self.cleaned_data["multidates_planning_date_fin"]:
                self.add_error("multidates_planning_date_fin", "La date de fin doit être supérieure à la date de début")
                return
            if not self.cleaned_data["multidates_planning_jours_scolaires"] and not self.cleaned_data["multidates_planning_jours_vacances"]:
                self.add_error("multidates_planning_jours_scolaires", "Vous devez cocher au moins un jour scolaire ou un jour de vacances")
                return

            liste_dates = utils_dates.Calcule_dates_planning(date_debut=self.cleaned_data["multidates_planning_date_debut"],
                                               date_fin=self.cleaned_data["multidates_planning_date_fin"],
                                               inclure_feries=self.cleaned_data["multidates_planning_inclure_feries"],
                                               jours_scolaires=self.cleaned_data["multidates_planning_jours_scolaires"],
                                               jours_vacances=self.cleaned_data["multidates_planning_jours_vacances"],
                                               frequence_type=self.cleaned_data["multidates_planning_frequence_type"])
            if not liste_dates:
                self.add_error("multidates_planning_date_debut","Aucune date n'a été trouvée dans ce planning")
                return

            self.cleaned_data["date"] = liste_dates[0]
            self.cleaned_data["multidates_planning"] = liste_dates

        return self.cleaned_data

    def save(self):
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get("cropper_data")
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.image)
        return form


EXTRA_SCRIPT = """
<style>
    #div_id_multidates_planning_jours_scolaires label {
        text-align: right;
    }
    #div_id_multidates_planning_jours_vacances label {
        text-align: right;
    }
</style>

<script>

// type_nbre_places
function On_change_type_nbre_places() {
    $('#div_id_capacite_max').hide();
    if($(this).val() == 'OUI') {
        $('#div_id_capacite_max').show();
    }
}
$(document).ready(function() {
    $('#id_type_nbre_places').change(On_change_type_nbre_places);
    On_change_type_nbre_places.call($('#id_type_nbre_places').get(0));
});

// type_tarification
function On_change_type_tarification() {
    $('#div_id_montant').hide();
    $('#div_id_copie_evenement').hide();
    if($(this).val() == 'SIMPLE') {
        $('#div_id_montant').show();
    }
    if($(this).val() == 'EXISTANT') {
        $('#div_id_copie_evenement').show();
    }
}
$(document).ready(function() {
    $('#id_type_tarification').change(On_change_type_tarification);
    On_change_type_tarification.call($('#id_type_tarification').get(0));
});

// Mode de saisie date
function On_change_mode_saisie() {
    $('#div_id_date').hide();
    $('#div_id_multidates_saisie').hide();
    $('#div_id_multidates_calendrier').hide();
    $('#div_id_multidates_planning').hide();
    if ($(this).val() == "UNIQUE") {
        $('#div_id_date').show();
    }
    if ($(this).val() == "MULTIDATES_SAISIE") {
        $('#div_id_multidates_saisie').show();
    }
    if ($(this).val() == "MULTIDATES_CALENDRIER") {
        $('#div_id_multidates_calendrier').show();
    }
    if ($(this).val() == "MULTIDATES_PLANNING") {
        $('#div_id_multidates_planning').show();
    }
}
$(document).ready(function() {
    $('#id_mode_saisie').change(On_change_mode_saisie);
    On_change_mode_saisie.call($('#id_mode_saisie').get(0));
});

</script>
"""