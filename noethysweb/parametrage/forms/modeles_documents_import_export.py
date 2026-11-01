# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import ModeleDocument, Structure, CHOIX_CATEGORIE_MODELE_DOCUMENT
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    action = forms.ChoiceField(label="Action", choices=[("EXPORTER", "Exporter"), ("IMPORTER", "Importer")], initial="EXPORTER", required=False)
    selection_modeles_exportables = forms.MultipleChoiceField(label="Sélection des modèles", choices=[], widget=forms.SelectMultiple(attrs={"size": 15}), required=False,
                                                             help_text="Vous pouvez utiliser CTRL ou MAJ pour sélectionner plusieurs modèles. Les calques de fond utilisés par les modèles sélectionnés sont exportés automatiquement.")
    fichier = forms.FileField(label="Fichier d'import", widget=forms.FileInput(attrs={"accept": ".nwd"}), required=False,
                              help_text="Sélectionnez le fichier à importer (Extension NWD).", validators=[FileExtensionValidator(allowed_extensions=["nwd"])])
    selection_modeles_importables = forms.CharField(widget=forms.HiddenInput(), required=False)
    selection_structure = forms.ModelChoiceField(label="Structure associée", queryset=Structure.objects.none(), required=False, empty_label="Toutes les structures",
                                                 help_text="Sélectionnez la structure qui sera associée aux modèles importés. Laissez 'Toutes les structures' pour qu'ils soient disponibles dans toutes les structures.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"
        self.helper.use_custom_control = False

        # Sélection des modèles accessibles à l'utilisateur, regroupés par catégorie
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        modeles = ModeleDocument.objects.filter(condition_structure).order_by("nom")
        choices = []
        for code_categorie, label_categorie in CHOIX_CATEGORIE_MODELE_DOCUMENT:
            liste_modeles = [(modele.pk, modele.nom) for modele in modeles if modele.categorie == code_categorie]
            if liste_modeles:
                choices.append((label_categorie, liste_modeles))
        self.fields["selection_modeles_exportables"].choices = choices

        # Importe uniquement les structures de l'utilisateur en cours
        self.fields["selection_structure"].queryset = self.request.user.structures.all()

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_documents_liste' %}", enregistrer=False, ajouter=False,
                      commandes_principales=[HTML(
                          """<a type='button' class="btn btn-primary margin-r-5" onclick="executer()" title="Exécuter"><i class='fa fa-bolt margin-r-5'></i>Exécuter</a>"""),
                      ]),
            Fieldset("Action",
                Field("action"),
            ),
            Fieldset("Paramètres",
                Field("selection_modeles_exportables"),
                Field("fichier"),
                Field("selection_structure"),
            ),
            Field("selection_modeles_importables"),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        # Exporter
        if self.cleaned_data["action"] == "EXPORTER":
            if not self.cleaned_data["selection_modeles_exportables"]:
                self.add_error("selection_modeles_exportables", "Vous devez sélectionner au moins un modèle dans la liste.")
        # Importer
        if self.cleaned_data["action"] == "IMPORTER":
            if not self.cleaned_data.get("fichier", None):
                self.add_error("fichier", "Vous devez sélectionner un fichier d'import sur votre ordinateur.")
        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_action() {
        $("#div_id_selection_modeles_exportables").hide();
        $("#div_id_fichier").hide();
        $("#div_id_selection_structure").hide();
        if ($("#id_action").val() == "EXPORTER") {
            $("#div_id_selection_modeles_exportables").show();
        };
        if ($("#id_action").val() == "IMPORTER") {
            $("#div_id_fichier").show();
            $("#div_id_selection_structure").show();
        };
    }
    $(document).ready(function() {
        $("#id_action").on("change", On_change_action);
        On_change_action.call($("#id_action").get(0));
        // Réinitialise la sélection des modèles importables si le fichier change
        $("#id_fichier").on("change", function() {
            $("#id_selection_modeles_importables").val("");
        });
    });
</script>
"""
