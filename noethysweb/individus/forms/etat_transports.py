# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils.utils_texte import Creation_tout_cocher
from core.widgets import DatePickerWidget
from core.models import CATEGORIES_TRANSPORTS


# Les 40 états disponibles, regroupés par catégorie pour l'affichage (optgroups)
# Le premier élément de chaque tuple est le code interne utilisé par Impression.Draw()
CHOIX_TYPES_ETATS = [
    ("Regroupements simples", [
        ("par_mode", "1 - Par mode de transport"),
        ("par_ligne", "2 - Par ligne de transport"),
        ("par_arret", "3 - Par arrêt (prise en charge)"),
        ("par_ligne_arret", "4 - Par ligne puis par arrêt"),
        ("par_compagnie", "5 - Par compagnie de transport"),
        ("par_compagnie_ligne", "6 - Par compagnie puis par ligne"),
        ("par_activite", "7 - Par activité concernée"),
        ("par_famille", "8 - Par famille"),
        ("par_ecole", "9 - Par école"),
        ("par_lieu", "21 - Par lieu (gare, aéroport, port)"),
        ("par_destination", "22 - Par destination (arrivée)"),
        ("par_age", "37 - Par tranche d'âge"),
    ]),
    ("Tris chronologiques", [
        ("chrono_depart", "10 - Chronologique (heure de départ)"),
        ("chrono_arrivee", "11 - Chronologique (heure d'arrivée)"),
        ("par_sens", "12 - Par sens (Aller / Retour)"),
        ("par_creneau", "23 - Par créneau horaire"),
        ("par_duree", "24 - Par durée de trajet"),
        ("chrono_global", "25 - Chronologique global (repères Matin/Soir)"),
        ("occupation_ligne", "39 - Occupation cumulée par ligne"),
    ]),
    ("Filtres", [
        ("ponctuels", "13 - Transports ponctuels uniquement"),
        ("programmes", "14 - Transports programmés uniquement"),
        ("observations", "15 - Avec observations (PAI, etc.)"),
        ("par_numero", "28 - Par numéro de transport"),
        ("multi_activites", "31 - Transports concernant plusieurs activités"),
    ]),
    ("Vues consolidées", [
        ("aller_retour", "19 - Vue aller-retour consolidée"),
        ("multi_trajets", "30 - Multi-trajets par individu"),
        ("ordre_arrets", "33 - Par ligne, dans l'ordre des arrêts"),
        ("pivot_ligne_creneau", "34 - Tableau croisé Ligne × Créneau"),
        ("statistique", "17 - Récapitulatif statistique"),
    ]),
    ("Formats spéciaux", [
        ("etiquettes", "18 - Étiquettes nominatives"),
        ("etiquettes_codebarres", "36 - Étiquettes avec code-barres"),
        ("emargement", "32 - Feuille d'émargement"),
        ("affichage_public", "35 - Format affichage public (grande police)"),
        ("par_transporteur", "20 - Feuille de route par transporteur"),
    ]),
    ("Contrôles / anomalies", [
        ("anomalies_infos", "16 - Anomalies (infos manquantes)"),
        ("sans_transport", "27 - Individus inscrits sans transport affecté"),
        ("traca_prog", "26 - Traçabilité : ponctuels issus d'une programmation"),
        ("justif_jour", "29 - Justificatif jour scolaire / jour de vacances"),
        ("prog_desactivees", "38 - Programmations désactivées (à vérifier)"),
        ("controle_presence", "40 - Contrôle de cohérence transport / présence"),
    ]),
]


class Formulaire(FormulaireBase, forms.Form):
    date = forms.DateField(label="Date", required=True, widget=DatePickerWidget(attrs={"afficher_fleches": True}))

    type_etat = forms.ChoiceField(label="Type d'état", required=True, choices=CHOIX_TYPES_ETATS, initial="par_mode")

    categories = forms.MultipleChoiceField(
        label="", required=True, widget=forms.CheckboxSelectMultiple,
        choices=CATEGORIES_TRANSPORTS, initial=[code for code, label in CATEGORIES_TRANSPORTS],
        help_text=Creation_tout_cocher("categories"),
    )

    inclure_ponctuels = forms.BooleanField(label="Transports ponctuels", required=False, initial=True,
        help_text="Transports saisis avec une date de départ/arrivée précise")
    inclure_programmes = forms.BooleanField(label="Transports programmés (récurrents)", required=False, initial=True,
        help_text="Transports définis sur une période avec des jours de la semaine récurrents")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'individus_toc' %}", enregistrer=False, ajouter=False,
                commandes_principales=[HTML(
                    """<a type='button' class="btn btn-primary margin-r-5" onclick="generer_pdf()" title="Génération du PDF"><i class='fa fa-file-pdf-o margin-r-5'></i>Générer le PDF</a>"""),
                ]),
            Fieldset("Sélection",
                Field("date"),
                Field("type_etat"),
                HTML("""<div class="row"><div class="col-md-10 offset-md-2"><div id="description_etat" class="text-muted" style="margin-top:-10px; margin-bottom:15px;"></div></div></div>"""),
            ),
            Fieldset("Types de transports",
                Div(
                    Field("inclure_ponctuels"),
                    Field("inclure_programmes"),
                ),
            ),
            Fieldset("Modes de transport",
            Div(
                Div(css_class="col-md-2"),  # colonne vide, à la place du label
                Div(InlineCheckboxes("categories"), css_class="col-md-10"),
                css_class="row",
                ),
            ),
        )

    def clean(self):
        cleaned_data = super(Formulaire, self).clean()
        if not cleaned_data.get("categories"):
            self.add_error("categories", "Vous devez cocher au moins un mode de transport")
        if not cleaned_data.get("inclure_ponctuels") and not cleaned_data.get("inclure_programmes"):
            self.add_error("inclure_ponctuels", "Vous devez cocher au moins un type de transport")
        return cleaned_data
