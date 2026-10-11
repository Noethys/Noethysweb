# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.forms.accordeon import Accordeon, Section
from core.forms.select2 import Select2MultipleWidget
from core.models import LISTE_ETATS_CONSO
from core.widgets import DateRangePickerWidget, SelectionActivitesWidget
from core.utils import utils_parametres
from outils.utils.utils_rapport_activite import RUBRIQUES, RUBRIQUES_DEFAUT, TRANCHES_QF_DEFAUT

CATEGORIE_PARAMETRES = "rapport_activite"
COULEURS_PRINCIPALES = ["#185FA5", "#0F6E56", "#534AB7", "#993C1D", "#993556", "#444441"]
COULEURS_COMPARAISON = ["#B4B2A9", "#85B7EB", "#F0997B", "#97C459"]

# Paramètres mémorisables avec leur valeur par défaut (le type sert à la conversion depuis la base)
PARAMETRES_DEFAUT = {
    "periode_type": "annee_civile",
    "activites": json.dumps({"type": "toutes", "ids": []}),
    "etats": ["reservation", "present"],
    "rubriques": RUBRIQUES_DEFAUT,
    "tranches_qf": TRANCHES_QF_DEFAUT,
    "comparer": True,
    "analyses": True,
    "sommaire": True,
    "numeros_page": True,
    "annexes": False,
    "valeurs_graphiques": True,
    "titre": "",
    "sous_titre": "",
    "introduction": "",
    "pied_page": "",
    "couleur_principale": COULEURS_PRINCIPALES[0],
    "couleur_comparaison": COULEURS_COMPARAISON[0],
    "police": "helvetica",
    "taille": "9",
    "style_garde": "bandeau",
    "logo_source": "organisateur",
}


def Get_annee_defaut():
    """ Dernière année civile complète """
    return datetime.date.today().year - 1


def Get_annee_scolaire_defaut():
    """ Dernière année scolaire terminée (septembre à août) """
    aujourdhui = datetime.date.today()
    return aujourdhui.year - 1 if aujourdhui.month >= 9 else aujourdhui.year - 2


class Formulaire(FormulaireBase, forms.Form):
    # Période et données
    periode_type = forms.ChoiceField(label="Période", choices=[("annee_civile", "Année civile"), ("annee_scolaire", "Année scolaire (septembre à août)"),
                                                                ("personnalisee", "Période personnalisée")], initial="annee_civile", required=True)
    annee = forms.IntegerField(label="Année", required=False, min_value=1990, max_value=2100)
    annee_scolaire = forms.ChoiceField(label="Année scolaire", required=False, choices=[])
    periode = forms.CharField(label="Dates", required=False, widget=DateRangePickerWidget())
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": False, "afficher_toutes": True}))
    etats = forms.MultipleChoiceField(label="États des consommations", required=True, widget=Select2MultipleWidget(), choices=LISTE_ETATS_CONSO,
                                      help_text="Consommations prises en compte pour la fréquentation, le public et les familles.")
    tranches_qf = forms.CharField(label="Tranches de quotient familial", required=False, help_text="Format : 0-500;501-800;801-1100;etc.")
    rubriques = forms.MultipleChoiceField(label="Rubriques", required=True, choices=[(code, titre) for code, titre, description in RUBRIQUES],
                                          widget=forms.CheckboxSelectMultiple)

    # Contenu
    comparer = forms.BooleanField(label="Comparer avec la période précédente (N-1)", required=False)
    analyses = forms.BooleanField(label="Analyses rédigées automatiquement", required=False)
    sommaire = forms.BooleanField(label="Sommaire paginé", required=False)
    numeros_page = forms.BooleanField(label="Numéros de page", required=False)
    valeurs_graphiques = forms.BooleanField(label="Afficher les valeurs sur les graphiques", required=False)
    annexes = forms.BooleanField(label="Annexes détaillées (tableaux mensuels)", required=False)

    # Textes
    titre = forms.CharField(label="Titre du rapport", required=False, max_length=150, help_text="Laissez vide pour un titre automatique.")
    sous_titre = forms.CharField(label="Sous-titre", required=False, max_length=150)
    introduction = forms.CharField(label="Texte d'introduction", required=False, widget=forms.Textarea(attrs={"rows": 3}), max_length=3000)
    pied_page = forms.CharField(label="Texte de pied de page", required=False, max_length=150, help_text="Par défaut : nom de l'organisateur.")

    # Mise en page
    couleur_principale = forms.CharField(label="Couleur principale", required=False, widget=forms.TextInput(attrs={"type": "color"}))
    couleur_comparaison = forms.CharField(label="Couleur de comparaison (N-1)", required=False, widget=forms.TextInput(attrs={"type": "color"}))
    police = forms.ChoiceField(label="Police", choices=[("helvetica", "Helvetica"), ("times", "Times")], widget=forms.RadioSelect, required=True)
    taille = forms.ChoiceField(label="Taille du texte", choices=[("8", "Petite (8 pt)"), ("9", "Normale (9 pt)"), ("10", "Grande (10 pt)"), ("11", "Très grande (11 pt)")], required=True)
    style_garde = forms.ChoiceField(label="Page de garde", choices=[("bandeau", "Avec bandeau de couleur"), ("sobre", "Sobre"), ("aucune", "Sans page de garde")], required=True)
    logo_source = forms.ChoiceField(label="Logo", choices=[("organisateur", "Logo de l'organisateur"), ("personnalise", "Importer une autre image"), ("aucun", "Aucun logo")], required=True)
    logo_fichier = forms.ImageField(label="Image du logo", required=False, help_text="Formats PNG ou JPG. Cette image n'est pas mémorisée.")
    memoriser = forms.BooleanField(label="Mémoriser ces réglages pour mes prochains rapports", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_rapport_activite"
        self.helper.form_tag = False

        # Années scolaires proposées
        annee_scolaire = Get_annee_scolaire_defaut()
        self.fields["annee_scolaire"].choices = [(str(a), "%d-%d" % (a, a + 1)) for a in range(annee_scolaire + 1, annee_scolaire - 10, -1)]
        self.fields["annee_scolaire"].initial = str(annee_scolaire)
        self.fields["annee"].initial = Get_annee_defaut()
        self.fields["periode"].initial = "%s;%s" % (datetime.date(Get_annee_defaut(), 1, 1), datetime.date(Get_annee_defaut(), 12, 31))

        # Valeurs mémorisées
        if self.request and not self.is_bound:
            parametres = utils_parametres.Get_categorie(categorie=CATEGORIE_PARAMETRES, utilisateur=self.request.user, parametres=PARAMETRES_DEFAUT)
            for nom, valeur in parametres.items():
                if nom in self.fields:
                    self.fields[nom].initial = valeur

        self.helper.layout = Layout(
            Accordeon(
                Section("Période et données",
                    Field("periode_type"),
                    Field("annee"),
                    Field("annee_scolaire"),
                    Field("periode"),
                    Field("activites"),
                    Field("etats"),
                    Field("tranches_qf"),
                ),
                Section("Contenu",
                    Field("comparer"),
                    Field("analyses"),
                    Field("sommaire"),
                    Field("numeros_page"),
                    Field("valeurs_graphiques"),
                    Field("annexes"),
                ),
                Section("Textes",
                    Field("titre"),
                    Field("sous_titre"),
                    Field("introduction"),
                    Field("pied_page"),
                ),
                Section("Mise en page du PDF",
                    Row(
                        Column(Field("couleur_principale"), HTML(Html_nuancier("couleur_principale", COULEURS_PRINCIPALES)), css_class="col-6"),
                        Column(Field("couleur_comparaison"), HTML(Html_nuancier("couleur_comparaison", COULEURS_COMPARAISON)), css_class="col-6"),
                    ),
                    Row(
                        Column(Field("police"), css_class="col-6"),
                        Column(Field("taille"), css_class="col-6"),
                    ),
                    Field("style_garde"),
                    Field("logo_source"),
                    Field("logo_fichier"),
                ),
                css_id="accordeon_rapport",
            ),
            Field("memoriser"),
        )

    def clean_activites(self):
        try:
            selection = json.loads(self.cleaned_data["activites"])
        except Exception:
            raise forms.ValidationError("La sélection des activités n'est pas valide")
        if selection.get("type") != "toutes" and not selection.get("ids"):
            raise forms.ValidationError("Vous devez sélectionner au moins une activité ou choisir « Toutes les activités »")
        return self.cleaned_data["activites"]

    def clean(self):
        cleaned_data = super(Formulaire, self).clean()
        periode_type = cleaned_data.get("periode_type")
        if periode_type == "annee_civile" and not cleaned_data.get("annee"):
            self.add_error("annee", "Vous devez saisir une année")
        if periode_type == "annee_scolaire" and not cleaned_data.get("annee_scolaire"):
            self.add_error("annee_scolaire", "Vous devez sélectionner une année scolaire")
        if periode_type == "personnalisee" and not cleaned_data.get("periode"):
            self.add_error("periode", "Vous devez sélectionner une période")
        if cleaned_data.get("logo_source") == "personnalise" and not cleaned_data.get("logo_fichier"):
            self.add_error("logo_fichier", "Vous devez sélectionner une image")
        return cleaned_data

    def Get_periode(self):
        """ Renvoie (date_debut, date_fin, label N, label N-1) """
        donnees = self.cleaned_data
        if donnees["periode_type"] == "annee_civile":
            annee = donnees["annee"]
            return datetime.date(annee, 1, 1), datetime.date(annee, 12, 31), str(annee), str(annee - 1)
        if donnees["periode_type"] == "annee_scolaire":
            annee = int(donnees["annee_scolaire"])
            return datetime.date(annee, 9, 1), datetime.date(annee + 1, 8, 31), "%d-%d" % (annee, annee + 1), "%d-%d" % (annee - 1, annee)
        date_debut, date_fin = [datetime.date.fromisoformat(d) for d in donnees["periode"].split(";")]
        return date_debut, date_fin, "la période", "la période précédente"

    def Get_parametres_a_memoriser(self):
        return {nom: self.cleaned_data.get(nom) if not isinstance(defaut, bool) else bool(self.cleaned_data.get(nom)) for nom, defaut in PARAMETRES_DEFAUT.items()}


def Html_nuancier(nom_champ="", couleurs=[]):
    """ Pastilles de couleurs prédéfinies sous le sélecteur de couleur """
    boutons = "".join("""<button type="button" class="btn btn-sm rapport-pastille" style="background-color:%s;" data-couleur="%s" data-champ="id_%s" title="%s" aria-label="Couleur %s"></button>""" % (c, c, nom_champ, c, c) for c in couleurs)
    return """<div class="rapport-nuancier mb-3">%s</div>""" % boutons
