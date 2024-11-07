# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django import forms
from django.forms import ModelForm
from django.db.models import Max
from core.forms.select2 import Select2MultipleWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Hidden, Fieldset, Div
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import CommandeModeleColonne, Unite, Groupe


LISTE_CHOIX_COLONNES = [
    ("NUMERIQUE_CONSO", "Numérique : Quantité de consommations"),
    ("NUMERIQUE_SUGGESTION", "Numérique : Quantité de consommations (Avec suggestions)"),
    ("NUMERIQUE_LIBRE", "Numérique : Libre"),
    ("NUMERIQUE_TOTAL", "Numérique : Total"),
    ("TEXTE_LIBRE", "Texte : Libre"),
    ("TEXTE_INFOS", "Texte : Informations"),
]

class Formulaire(FormulaireBase, ModelForm):
    # Catégorie
    categorie = forms.ChoiceField(label="Catégorie", choices=LISTE_CHOIX_COLONNES, initial="NUMERIQUE_CONSO", required=True)

    # Numérique conso
    unites_conso = forms.MultipleChoiceField(label="Unités de consommation", required=False, widget=Select2MultipleWidget(), choices=[], help_text="Sélectionnez les unités à additionner.")
    unites_suggestions = forms.MultipleChoiceField(label="Unités de consommation", required=False, widget=Select2MultipleWidget(), choices=[], help_text="Sélectionnez les unités à additionner.")

    # Colonne total
    colonnes = forms.MultipleChoiceField(label="Colonnes", required=False, widget=Select2MultipleWidget(), choices=[], help_text="Sélectionnez les colonnes numériques à additionner.")

    # Texte informations
    type_infos = forms.ChoiceField(label="Informations", choices=[("REGIMES", "Régimes alimentaires"), ("INFOS", "Informations personnelles")], initial="REGIMES", required=False)
    groupes = forms.MultipleChoiceField(label="Groupes", required=False, widget=Select2MultipleWidget(), choices=[], help_text="Sélectionnez les groupes concernés.")

    class Meta:
        model = CommandeModeleColonne
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idmodele = kwargs.pop("categorie")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "commandes_modeles_colonnes_form"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Ordre
        if self.instance.ordre == None:
            max = CommandeModeleColonne.objects.aggregate(Max("ordre"))["ordre__max"]
            if max == None:
                max = 0
            self.fields["ordre"].initial = max + 1
        else:
            self.fields["ordre"].initial = self.instance.ordre

        # Numérique avec suggestion
        groupes = {}
        for groupe in Groupe.objects.all().order_by("ordre"):
            groupes.setdefault(groupe.activite_id, [])
            groupes[groupe.activite_id].append(groupe)
        unites = []
        for unite in Unite.objects.select_related("activite").order_by("-activite__date_fin", "activite__nom", "ordre"):
            for groupe in groupes.get(unite.activite_id):
                unites.append(("%d_%d" % (unite.pk, groupe.pk), "%s : %s - %s" % (unite.activite.nom, unite.nom, groupe.nom)))
        self.fields["unites_conso"].choices = unites
        self.fields["unites_suggestions"].choices = unites

        # Colonne total
        liste_colonnes = CommandeModeleColonne.objects.filter(modele=idmodele, categorie__in=["NUMERIQUE_LIBRE", "NUMERIQUE_CONSO", "NUMERIQUE_SUGGESTION"]).exclude(pk=self.instance.pk).order_by("ordre")
        self.fields["colonnes"].choices = [(colonne.pk, colonne.nom) for colonne in liste_colonnes]

        # Texte informations
        liste_groupes = Groupe.objects.select_related("activite").order_by("-activite__date_fin", "activite__nom", "ordre")
        self.fields["groupes"].choices = [(groupe.pk, "%s : %s" % (groupe.activite.nom, groupe.nom)) for groupe in liste_groupes]

        # Importation des paramètres
        if self.instance.parametres:
            dict_parametres = json.loads(self.instance.parametres)
            for key, valeurs in dict_parametres.items():
                if key == "unites":
                    key = "unites_suggestions" if "SUGGESTION" in self.instance.categorie else "unites_conso"
                self.fields[key].initial = valeurs

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden("modele", value=idmodele),
            Hidden("largeur", value=80),
            Hidden("ordre", value=self.fields["ordre"].initial),
            Fieldset("Généralités",
                Field("nom"),
                Field("categorie"),
            ),
            Fieldset("Paramètres",
                Div(
                    HTML("<center>Aucun paramètre à renseigner</center>"),
                    id="TEXTE_LIBRE"
                ),
                Div(
                    HTML("<center>Aucun paramètre à renseigner</center>"),
                    id="NUMERIQUE_LIBRE"
                ),
                Div(
                    Field("unites_conso"),
                    id="NUMERIQUE_CONSO"
                ),
                Div(
                    Field("unites_suggestions"),
                    id="NUMERIQUE_SUGGESTION"
                ),
                Div(
                    Field("colonnes"),
                    id="NUMERIQUE_TOTAL"
                ),
                Div(
                    Field("type_infos"),
                    Field("groupes"),
                    id="TEXTE_INFOS"
                ),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # NUMERIQUE_CONSO
        if self.cleaned_data.get("categorie") == "NUMERIQUE_CONSO":
            if not self.cleaned_data["unites_conso"]:
                self.add_error("unites_conso", "Vous devez sélectionner au moins une unité de consommation")
            self.cleaned_data["parametres"] = json.dumps({"unites": self.cleaned_data.get("unites_conso")})

        # NUMERIQUE_SUGGESTION
        if self.cleaned_data.get("categorie") == "NUMERIQUE_SUGGESTION":
            if not self.cleaned_data["unites_suggestions"]:
                self.add_error("unites_suggestions", "Vous devez sélectionner au moins une unité de consommation")
            self.cleaned_data["parametres"] = json.dumps({"unites": self.cleaned_data.get("unites_suggestions")})

        # NUMERIQUE_TOTAL
        if self.cleaned_data.get("categorie") == "NUMERIQUE_TOTAL":
            if not self.cleaned_data["colonnes"]:
                self.add_error("colonnes", "Vous devez sélectionner au moins une colonne")
            self.cleaned_data["parametres"] = json.dumps({"colonnes": self.cleaned_data.get("colonnes")})

        # NUMERIQUE_TOTAL
        if self.cleaned_data.get("categorie") == "TEXTE_INFOS":
            if not self.cleaned_data["groupes"]:
                self.add_error("groupes", "Vous devez sélectionner au moins un groupe")
            self.cleaned_data["parametres"] = json.dumps({"type_infos": self.cleaned_data.get("type_infos"), "groupes": self.cleaned_data.get("groupes")})

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>

// Catégorie
function On_change_categorie() {
    $("#NUMERIQUE_LIBRE").hide();
    $("#NUMERIQUE_CONSO").hide();
    $("#NUMERIQUE_SUGGESTION").hide();
    $("#NUMERIQUE_TOTAL").hide();
    $("#TEXTE_LIBRE").hide();
    $("#TEXTE_INFOS").hide();
    $("#" + $(this).val()).show();
}
$(document).ready(function() {
    $("#id_categorie").change(On_change_categorie);
    On_change_categorie.call($("#id_categorie").get(0));
});

</script>
"""
