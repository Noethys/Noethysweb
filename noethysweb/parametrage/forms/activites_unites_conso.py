# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.db.models import Max
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Div, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Unite, Groupe, Activite, CategorieTarif
from core.widgets import DatePickerWidget
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    heure_debut = forms.TimeField(label="Heure de début par défaut", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Vous pouvez saisir ici l'heure de début par défaut qui sera enregistrée lors de la saisie d'une consommation.")
    heure_fin = forms.TimeField(label="Heure de fin par défaut", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Vous pouvez saisir ici l'heure de fin par défaut qui sera enregistrée lors de la saisie d'une consommation.")
    heure_debut_min = forms.TimeField(label="Heure de début min.", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Heure de début minimale autorisée lors de la saisie.")
    heure_debut_max = forms.TimeField(label="Heure de début max.", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Heure de début maximale autorisée lors de la saisie.")
    heure_fin_min = forms.TimeField(label="Heure de fin min.", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Heure de fin minimale autorisée lors de la saisie.")
    heure_fin_max = forms.TimeField(label="Heure de fin max.", required=False, widget=forms.TimeInput(attrs={'type': 'time'}), help_text="Heure de fin maximale autorisée lors de la saisie.")

    # Durée de validité
    choix_validite = [("ILLIMITEE", "Durée illimitée"), ("LIMITEE", "Durée limitée")]
    validite_type = forms.TypedChoiceField(label="Type de validité", choices=choix_validite, initial='ILLIMITEE', required=True, help_text="Généralement, la durée sera illimitée. A modifier uniquement si vous souhaitez masquer cette unité de la grille des consommations à partir d'une date donnée (Dans le cas d'une unité obsolète par exemple).")
    validite_date_debut = forms.DateField(label="Date de début*", required=False, widget=DatePickerWidget())
    validite_date_fin = forms.DateField(label="Date de fin*", required=False, widget=DatePickerWidget())

    # Groupes
    choix_groupes = [("TOUS", "Tous les groupes"), ("SELECTION", "Uniquement certains groupes")]
    groupes_type = forms.TypedChoiceField(label="Groupes associés", choices=choix_groupes, initial='TOUS', required=True, help_text="A renseigner si vous souhaitez que cette unité apparaisse uniquement dans la grille des consommations des individus inscrits sur un groupe donné. Exemple : Pour afficher une unité 'Sieste' uniquement pour les enfants du groupe 'Maternel'.")
    groupes = forms.ModelMultipleChoiceField(label="Sélection des groupes", widget=Select2MultipleWidget(), queryset=Groupe.objects.none(), required=False)

    # Catégories de tarifs
    choix_categories = [("TOUS", "Toutes les catégories de tarifs"), ("SELECTION", "Uniquement certaines catégories de tarifs")]
    categories_tarifs_type = forms.TypedChoiceField(label="Catégories de tarifs associées", choices=choix_categories, initial='TOUS', required=True, help_text="A renseigner uniquement pour que cette unité apparaisse dans la grille des consommations des individus inscrits sur une catégorie de tarif donnée. Exemple : Pour afficher une unité 'Transport' pour les enfants inscrits avec la catégorie de tarif 'Hors commune'.")
    categories_tarifs = forms.ModelMultipleChoiceField(label="Sélection des catégories", widget=Select2MultipleWidget(), queryset=CategorieTarif.objects.none(), required=False)

    # Incompatibilités
    incompatibilites = forms.ModelMultipleChoiceField(label="Incompatibilités", widget=Select2MultipleWidget(), queryset=Unite.objects.none(), required=False,
                                                      help_text="Sélectionnez les unités qui ne peuvent pas être saisies en même temps que cette unité. Exemple : Une unité 'Matin' qui ne pourrait pas être saisie en même temps qu'une 'Journée'.")

    # Dépendances
    dependances = forms.ModelMultipleChoiceField(label="Unités liées", widget=Select2MultipleWidget(), queryset=Unite.objects.none(), required=False,
                                                 help_text="Cette unité héritera de l'état des unités liées et sera supprimée en cas d'absence de l'une des unités liées. Par exemple, un repas ne peut exister seul s'il n'y pas de journée, de matinée ou d'après-midi saisies.")

    class Meta:
        model = Unite
        fields = ["ordre", "activite", "nom", "abrege", "type", "heure_debut", "heure_fin", "heure_debut_fixe", "heure_fin_fixe",
                  "repas", "restaurateur", "touche_raccourci", "date_debut", "date_fin", "groupes", "categories_tarifs", "incompatibilites", "visible_portail", "imposer_saisie_valeur",
                  "heure_debut_min", "heure_debut_max", "heure_fin_min", "heure_fin_max", "equiv_journees", "equiv_heures", "dependances"]
        help_texts = {
            "nom": "Saisissez le nom de l'unité. Exemple : Journée, Matin, repas, Séance, Atelier...",
            "abrege": "Saisissez quelques caractères en majuscules ou des chiffres. Exemples : J, M, R, SEANCE, ATELIER...",
            "type": """Sélectionnez le type de l'unité. 
                        Unitaire : Le plus utilisé, pour enregistrer simplement des consommations (Journée, Matin, Atelier...). 
                        Horaire : Pour imposer la saisie d'horaires de début et de fin pour chaque consommation (Pour une activité facturée au temps par exemple).
                        Quantité : Pour imposer la saisie d'une quantité (pour facturer par exemple 10 repas à une association pour une date donnée).
                        Multihoraires : Pour permettre de saisir plusieurs horaires dans une seule consommation (Pour enregistrer des allers et venues par exemple). 
                        Evenementiel : Pour autoriser la saisie de plusieurs évènements dans une seule unité de consommation. Très utilisé par les secteurs jeunes ou pour des sorties familiales par exemple.""",
            "equiv_journees": "Saisissez l'équivalence en journées (utile uniquement pour l'état global et l'état nominatif). Ex : une journée=1, une demi-journée=0.5, etc...",
            "equiv_heures": "Saisissez l'équivalence en heures (utile uniquement pour l'état global et l'état nominatif). Format : HH:MM.",
            "touche_raccourci": "Il suffira de conserver cette touche enfoncée pour saisir une consommation de cette unité en même temps qu'une autre dans la grille des consommations.",
            "visible_portail": "Décochez cette case uniquement si vous souhaitez que cette unité ne soit pas visible par un usager sur le planning de réservations du portail. Seuls les utilisateurs pourront la voir dans la grille des consommations.",
            "imposer_saisie_valeur": "Par défaut, un usager ne peut pas saisir d'horaire ou de quantité sur le portail. En cochant cette case, vous imposez à l'usager de renseigner cette information lors de la saisie de la réservation. Cette option n'est utile que si vous avez sélectionné un type Horaire ou Quantité.",
        }
        widgets = {
            "equiv_heures": forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_unites_conso_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "activite") == False:
            activite = Activite.objects.get(pk=idactivite)
        else:
            activite = self.instance.activite

        # Incompatibilités
        self.fields['incompatibilites'].queryset = Unite.objects.filter(activite=activite).exclude(pk=self.instance.pk)

        # Dépendances
        self.fields['dependances'].queryset = Unite.objects.filter(activite=activite).exclude(pk=self.instance.pk)

        # Importe la durée de validité
        if self.instance.date_fin in (None, datetime.date(2999, 1, 1)):
            self.fields['validite_type'].initial = "ILLIMITEE"
        else:
            self.fields['validite_type'].initial = "LIMITEE"
            self.fields['validite_date_debut'].initial = self.instance.date_debut
            self.fields['validite_date_fin'].initial = self.instance.date_fin

        # Ordre
        if self.instance.ordre == None:
            max = Unite.objects.filter(activite=activite).aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Importe les groupes
        self.fields['groupes'].queryset = Groupe.objects.filter(activite=activite)
        if self.instance.ordre != None:
            if len(self.instance.groupes.all()) > 0:
                self.fields['groupes_type'].initial = "SELECTION"

        # Importe les catégories de tarifs
        self.fields['categories_tarifs'].queryset = CategorieTarif.objects.filter(activite=activite)
        if self.instance.ordre != None:
            if len(self.instance.categories_tarifs.all()) > 0:
                self.fields['categories_tarifs_type'].initial = "SELECTION"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=activite.idactivite),
            Hidden('ordre', value=self.fields['ordre'].initial),
            Fieldset("Nom de l'unité",
                Field("nom"),
                Field("abrege"),
            ),
            Fieldset("Caractéristiques",
                Field("type"),
                Field("incompatibilites"),
                Field("repas"),
                Field("restaurateur"),
                Field("touche_raccourci"),
                Field("dependances"),
                Field("visible_portail"),
                Field("imposer_saisie_valeur"),
            ),
            Fieldset("Heure de début",
                Field("heure_debut"),
                Field("heure_debut_min"),
                Field("heure_debut_max"),
                Field("heure_debut_fixe"),
            ),
            Fieldset("Heure de fin",
                Field("heure_fin"),
                Field("heure_fin_min"),
                Field("heure_fin_max"),
                Field("heure_fin_fixe"),
            ),
            Fieldset("Equivalences",
                Field("equiv_journees"),
                Field("equiv_heures"),
            ),
            Fieldset("Durée de validité",
                Field("validite_type"),
                Div(
                    Field("validite_date_debut"),
                    Field("validite_date_fin"),
                    id="bloc_periode",
                ),
            ),
            Fieldset("Groupes associés",
                Field("groupes_type"),
                Field("groupes"),
            ),
            Fieldset("Catégories de tarifs associées",
                Field("categories_tarifs_type"),
                Field("categories_tarifs"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Durée de validité
        if self.cleaned_data["validite_type"] == "LIMITEE":
            if self.cleaned_data["validite_date_debut"] == None:
                self.add_error('validite_date_debut', "Vous devez sélectionner une date de début")
                return
            if self.cleaned_data["validite_date_fin"] == None:
                self.add_error('validite_date_fin', "Vous devez sélectionner une date de fin")
                return
            if self.cleaned_data["validite_date_debut"] > self.cleaned_data["validite_date_fin"] :
                self.add_error('validite_date_fin', "La date de fin doit être supérieure à la date de début")
                return
            self.cleaned_data["date_debut"] = self.cleaned_data["validite_date_debut"]
            self.cleaned_data["date_fin"] = self.cleaned_data["validite_date_fin"]
        else:
            self.cleaned_data["date_debut"] = datetime.date(1977, 1, 1)
            self.cleaned_data["date_fin"] = datetime.date(2999, 1, 1)

        # Groupes associés
        if self.cleaned_data["groupes_type"] == "SELECTION":
            if len(self.cleaned_data["groupes"]) == 0:
                self.add_error('groupes', "Vous devez cocher au moins un groupe")
                return
        else:
            self.cleaned_data["groupes"] = []

        # Catégories de tarifs associées
        if self.cleaned_data["categories_tarifs_type"] == "SELECTION":
            if len(self.cleaned_data["categories_tarifs"]) == 0:
                self.add_error('categories_tarifs', "Vous devez cocher au moins une catégorie de tarifs")
                return
        else:
            self.cleaned_data["categories_tarifs"] = []

        return self.cleaned_data



EXTRA_SCRIPT = """
<script>

// groupes_type
function On_change_groupes_type() {
    $('#div_id_groupes').hide();
    if($(this).val() == 'SELECTION') {
        $('#div_id_groupes').show();
    }
}
$(document).ready(function() {
    $('#id_groupes_type').change(On_change_groupes_type);
    On_change_groupes_type.call($('#id_groupes_type').get(0));
});


// categories_tarifs_type
function On_change_categories_tarifs_type() {
    $('#div_id_categories_tarifs').hide();
    if($(this).val() == 'SELECTION') {
        $('#div_id_categories_tarifs').show();
    }
}
$(document).ready(function() {
    $('#id_categories_tarifs_type').change(On_change_categories_tarifs_type);
    On_change_categories_tarifs_type.call($('#id_categories_tarifs_type').get(0));
});


// validite_type
function On_change_validite_type() {
    $('#bloc_periode').hide();
    if($(this).val() == 'LIMITEE') {
        $('#bloc_periode').show();
    }
}
$(document).ready(function() {
    $('#id_validite_type').change(On_change_validite_type);
    On_change_validite_type.call($('#id_validite_type').get(0));
});

// repas
function On_change_repas() {
    $('#div_id_restaurateur').hide();
    if(this.checked) {
        $('#div_id_restaurateur').show();
    }
}
$(document).ready(function() {
    $('#id_repas').change(On_change_repas);
    On_change_repas.call($('#id_repas'));
});


</script>
"""