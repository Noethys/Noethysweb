# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget, Profil_configuration, ColorPickerWidget
from core.utils import utils_parametres, utils_questionnaires
from core.utils.utils_texte import Creation_tout_cocher
from core.models import Regime, JOURS_SEMAINE, Parametre
from core.forms.base import FormulaireBase


class Form_selection_periode(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())

    def __init__(self, *args, **kwargs):
        super(Form_selection_periode, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_selection_periode'
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Field('periode'),
        )


class Form_profil_configuration(FormulaireBase, forms.Form):
    profil = forms.ModelChoiceField(label="Profil", queryset=Parametre.objects.none(), widget=Profil_configuration({"categorie": "etat_global"}), required=True)

    def __init__(self, *args, **kwargs):
        super(Form_profil_configuration, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_profil_configuration'
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False
        self.fields['profil'].queryset = Parametre.objects.filter(categorie="profil_etat_global").order_by("nom")
        self.helper.layout = Layout(
            Field('profil'),
        )


class Form_selection_activites(FormulaireBase, forms.Form):
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False}))

    def __init__(self, *args, **kwargs):
        super(Form_selection_activites, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_selection_activites'
        self.helper.form_method = 'post'
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Field('activites'),
        )



class Form_selection_options(FormulaireBase, forms.Form):
    # Regroupements
    liste_regroupements = [("aucun", "Aucun"), ("jour", "Jour"), ("mois", "Mois"), ("annee", "Année"),
        ("activite", "Activité"), ("groupe", "Groupe"), ("evenement", "Evènement"),
        ("evenement_date", "Evènement (avec date)"), ("etiquette", "Etiquette"),
        ("unite_conso", "Unité de consommation"), ("categorie_tarif", "Catégorie de tarif"),
        ("ville_residence", "Ville de résidence"), ("secteur", "Secteur géographique"),
        ("genre", "Genre (M/F)"), ("age", "Age"), ("ville_naissance", "Ville de naissance"),
        ("nom_ecole", "Ecole"), ("nom_classe", "Classe"), ("nom_niveau_scolaire", "Niveau scolaire"),
        ("individu", "Individu"), ("famille", "Famille"), ("regime", "Régime social"),
        ("caisse", "Caisse d'allocations"), ("qf_perso", "Quotient familial (tranches personnalisées)"),
        ("qf_tarifs", "Quotient familial (tranches paramétrées)"),
        ("qf_100", "Quotient familial (tranches de 100)"), ("categorie_travail", "Catégorie de travail"),
        ("categorie_travail_pere", "Catégorie de travail du père"),
        ("categorie_travail_mere", "Catégorie de travail de la mère")]

    # Intégration des questionnaires
    q = utils_questionnaires.Questionnaires()
    for public in ("famille", "individu"):
        for dictTemp in q.GetQuestions(public):
            label = "Question %s. : %s" % (public[:3], dictTemp["label"])
            code = "question_%s_%d" % (public, dictTemp["IDquestion"])
            liste_regroupements.append((code, label))

    regroupement_principal = forms.ChoiceField(label="Regroupement principal", choices=liste_regroupements, initial="aucun", required=False, help_text="Le regroupement principal permet d'obtenir un tableau de données par niveau de regroupement.")
    regroupement_age = forms.CharField(label="Regroupement par tranches d'âge", required=False, help_text="Saisissez les tranches d'âge souhaitées séparées par des virgules. Exemple : '3, 6, 12'.")
    tranches_qf_perso = forms.CharField(label="Regroupement par tranches de QF", required=False, help_text="Saisissez les tranches de QF souhaitées séparées par des virgules. Exemple : '650, 800, 1200'. A utiliser avec le regroupement principal 'Quotient familial (tranches personnalisées)'.")
    periodes_detaillees = forms.BooleanField(label="Regroupement par périodes détaillées", initial=True, required=False, help_text="Cochez cette case pour afficher les périodes détaillées.")

    # Données
    format_donnees = forms.ChoiceField(label="Format des données", choices=[("horaire", "Horaire"), ("decimal", "Décimal")], initial="horaire", required=False, help_text="Choisissez le format d'affichage des données: Horaire (Ex: 8h30) ou décimal (Ex: 8.5).")
    afficher_regime_inconnu = forms.BooleanField(label="Avertissement si régime famille inconnu", initial=True, required=False, help_text="Cochez cette case pour afficher un avertissement si le régime d'une ou plusieurs familles est inconnu.")
    liste_regimes = [("non", "Non")]
    try:
        liste_regimes.extend([(regime.pk, regime.nom) for regime in Regime.objects.all().order_by("nom")])
    except:
        pass
    associer_regime_inconnu = forms.ChoiceField(label="Associer régime inconnu à un régime", choices=liste_regimes, initial="non", required=False, help_text="Sélectionnez le régime dans lequel vous souhaitez inclure les familles au régime inconnu.")
    plafond_journalier_individu = forms.IntegerField(label="Plafond journalier par individu", initial=0, required=False, help_text="Saisissez un plafond journalier (en minutes) par individu, toutes activités confondues (0 = désactivé). Exemple : une valeur de 120 (minutes) plafonnera le temps retenu pour chaque individu à hauteur de 2 heures.")

    # Filtres
    jours_hors_vacances = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, initial=[0, 1, 2, 3, 4, 5, 6], help_text="Sélectionnez les jours hors vacances à inclure dans les calculs. %s." % Creation_tout_cocher("jours_hors_vacances"))
    jours_vacances = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, initial=[0, 1, 2, 3, 4, 5, 6], help_text="Sélectionnez les jours de vacances à inclure dans les calculs. %s." % Creation_tout_cocher("jours_vacances"))
    etat_consommations = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=[("reservation", "Réservation"), ("present", "Présent"), ("absentj", "Absence justifiée"), ("absenti", "Absence injustifiée")], initial=["reservation", "present", "absentj", "absenti"], help_text="Sélectionnez les états de consommations à inclure dans les calculs. %s." % Creation_tout_cocher("etat_consommations"))

    # Affichage
    orientation = forms.ChoiceField(label="Orientation de la page", choices=[("portrait", "Portrait"), ("paysage", "Paysage")], initial="portrait", required=False, help_text="Sélectionnez l'orientation de la page.")
    couleur_ligne_age = forms.CharField(label="Couleur de la ligne tranche d'âge", required=True, widget=ColorPickerWidget(), initial="#C0C0C0", help_text="Sélectionnez la couleur de la ligne tranche d'âge.")
    couleur_ligne_total = forms.CharField(label="Couleur de la ligne total", required=True, widget=ColorPickerWidget(), initial="#EAEAEA", help_text="Sélectionnez la couleur de la ligne total.")
    couleur_case_regroupement = forms.CharField(label="Couleur de la case regroupement principal", required=True, widget=ColorPickerWidget(), initial="#000000", help_text="Sélectionnez la couleur de la case regroupement principal.")
    couleur_texte_regroupement = forms.CharField(label="Couleur du texte regroupement principal", required=True, widget=ColorPickerWidget(), initial="#ffffff", help_text="Sélectionnez la couleur du texte regroupement principal.")

    def __init__(self, *args, **kwargs):
        super(Form_selection_options, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_selection_options'
        self.helper.form_method = 'post'
        self.helper.disable_csrf = True

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-4'
        self.helper.field_class = 'col-md-8'

        # Importation des paramètres
        # parametres = {nom: field.initial for nom, field in self.fields.items()}
        # del parametres["memoriser_parametres"]
        # parametres = utils_parametres.Get_categorie(categorie="impression_facture", parametres=parametres)
        # for nom, valeur in parametres.items():
        #     self.fields[nom].initial = valeur

        # Affichage
        self.helper.layout = Layout(
            Hidden("liste_parametres", ""),
            Fieldset("Regroupement",
                Field("regroupement_principal"),
                Field("regroupement_age"),
                Field("tranches_qf_perso"),
                Field("periodes_detaillees"),
            ),
            Fieldset("Données",
                Field("format_donnees"),
                Field("afficher_regime_inconnu"),
                Field("associer_regime_inconnu"),
                Field("plafond_journalier_individu"),
            ),
            Fieldset("Filtres",
                InlineCheckboxes("jours_hors_vacances"),
                InlineCheckboxes("jours_vacances"),
                InlineCheckboxes("etat_consommations"),
            ),
            Fieldset("Affichage",
                Field("orientation"),
                Field("couleur_ligne_age"),
                Field("couleur_ligne_total"),
                Field("couleur_case_regroupement"),
                Field("couleur_texte_regroupement"),
            ),
        )
