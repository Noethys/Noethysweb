# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.core.validators import FileExtensionValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.utils.utils_commandes import Commandes
from core.models import Activite, Structure
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    action = forms.ChoiceField(label="Action", choices=[("EXPORTER", "Exporter"), ("IMPORTER", "Importer")], initial="EXPORTER", required=False)
    selection_activites_exportables = forms.MultipleChoiceField(label="Sélection des activités", choices=[], help_text="Vous pouvez utiliser CTRL ou MAJ pour sélectionner plusieurs activités.", required=False)
    fichier = forms.FileField(label="Fichier d'import", widget=forms.FileInput(attrs={'accept':'text/nwa'}), help_text="Sélectionnez le fichier à importer (Extension NWA).", required=False, validators=[FileExtensionValidator(allowed_extensions=["nwa"])])
    selection_activites_importables = forms.CharField(widget=forms.HiddenInput(), required=False)
    selection_structure = forms.ModelChoiceField(label="Structure associée", queryset=Structure.objects.none(), required=False, help_text="Sélectionnez la structure qui sera associée aux activités importées.")
    donnees = forms.MultipleChoiceField(label="Données annexes à importer", required=False, widget=Select2MultipleWidget(), initial=[],
                                        choices=[("groupes_activites", "Groupes d'activités"), ("pieces", "Types de pièces"),("cotisations", "Types d'adhésion"), ("types_consentements", "Types de consentements")],
                                        help_text="Sélectionnez les données annexes à importer. Si vous utilisez cette option, veuillez à ne pas importer des données déjà existantes.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Sélection des activités
        activites = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("-date_fin", "nom")
        self.fields["selection_activites_exportables"].choices = [(activite.pk, activite.nom) for activite in activites]

        # Importe uniquement les structures de l'utilisateur en cours
        self.fields["selection_structure"].queryset = self.request.user.structures.all()

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'activites_liste' %}", enregistrer=False, ajouter=False,
                      commandes_principales=[HTML(
                          """<a type='button' class="btn btn-primary margin-r-5" onclick="executer()" title="Exécuter"><i class='fa fa-bolt margin-r-5'></i>Exécuter</a>"""),
                      ]),
            Fieldset("Action",
                Field("action"),
                     ),
            Fieldset("Paramètres",
                Field("selection_activites_exportables"),
                Field("fichier"),
                Field("selection_structure"),
                Field("donnees"),
            ),
            Field("selection_activites_importables"),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        # Exporter
        if self.cleaned_data["action"] == "EXPORTER":
            if not self.cleaned_data["selection_activites_exportables"]:
                self.add_error("selection_activites_exportables", "Vous devez sélectionner au moins une activité dans la liste.")
        # Importer
        if self.cleaned_data["action"] == "IMPORTER":
            if not self.cleaned_data.get("fichier", None):
                self.add_error("fichier", "Vous devez sélectionner un fichier d'import sur votre ordinateur.")
            if not self.cleaned_data["selection_structure"]:
                self.add_error("selection_structure", "Vous devez sélectionner la structure qui sera associée aux activités.")

        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_action() {
        $("#div_id_selection_activites_exportables").hide();
        $("#div_id_fichier").hide();
        $("#div_id_selection_structure").hide();
        $("#div_id_donnees").hide();
        if ($("#id_action").val() == "EXPORTER") {
            $("#div_id_selection_activites_exportables").show();
        };
        if ($("#id_action").val() == "IMPORTER") {
            $("#div_id_fichier").show();
            $("#div_id_selection_structure").show();
            $("#div_id_donnees").show();
        };
    }
    $(document).ready(function() {
        $("#id_action").on("change", On_change_action);
        On_change_action.call($("#id_action").get(0));
    });
</script>
"""
