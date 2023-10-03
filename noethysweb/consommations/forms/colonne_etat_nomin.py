# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import QuestionnaireQuestion


class Formulaire(FormulaireBase, forms.Form):
    nom = forms.CharField(label="Titre de la colonne", required=False)

    liste_choix = [
        ("aucun", "Aucune"),
        ("individu_nom_complet", "Nom complet de l'individu"),
        ("individu_nom", "Nom de l'individu"),
        ("individu_prenom", "Prénom de l'individu"),
        ("individu_sexe", "Genre (M/F)"),
        ("individu_date_naiss", "Date de naissance de l'individu"),
        ("individu_age", "Age de l'individu"),
        ("individu_adresse_complete", "Adresse complète de l'individu"),
        ("individu_rue", "Rue de l'individu"),
        ("individu_cp", "Code postal de l'individu"),
        ("individu_ville", "Ville de l'individu"),
        ("famille_nom_complet", "Noms des titulaires de la famille"),
        ("famille_num_allocataire", "Numéro d'allocataire de la famille"),
        ("famille_allocataire", "Nom de l'allocataire titulaire de la famille"),
        ("famille_caisse", "Nom de la caisse de la famille"),
        ("famille_qf", "Quotient familial de la famille"),
    ]

    # Ajout des questionnaires
    for categorie in ("individu", "famille"):
        for question in QuestionnaireQuestion.objects.filter(categorie=categorie, visible=True).order_by("ordre"):
            liste_choix.append(("question_%d" % question.pk, question.label))

    # Ajout des champs spécifiques aux consommations
    for champ, label_champ in [("*nbre_conso", "Nombre de consommations"), ("*temps_conso", "Temps réel des consommations"), ("*temps_facture", "Temps facturé"), ("*equiv_journees", "Equivalence journées"), ("*equiv_heures", "Equivalences heures")]:
        for suffixe, label_suffixe in [("", ""), ("_vacances", " durant les vacances"), ("_hors_vacances", " hors vacances")]:
            liste_choix.append((champ + suffixe, label_champ + label_suffixe))

    donnee = forms.ChoiceField(label="Donnée associée", choices=liste_choix, initial="aucun", required=False)

    # Filtre sur les unités de consommations
    filtre_unites = forms.TypedChoiceField(label="Filtre sur les unités de consommation", choices=[("TOUTES", "Toutes les unités"), ("SELECTION", "Uniquement les unités sélectionnées")], initial="TOUTES", required=False)
    unites = forms.CharField(label="Sélection d'unités", required=False, help_text="Saisissez le nom des unités de consommations à inclure dans les résultats, séparés par des points-virgule. Exemple : 'Accueil du matin;Accueil du soir'.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_colonne_etat_nomin'
        self.helper.form_method = 'post'
        self.helper.form_tag = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-4'
        self.helper.field_class = 'col-md-8'

        # Affichage
        self.helper.layout = Layout(
            Field("nom"),
            Field("donnee"),
            Field("filtre_unites"),
            Field("unites"),
        )
