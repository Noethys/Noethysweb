# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import PesModele, ModeleDocument, CHOIX_FORMAT_EXPORT_TRESOR


class Formulaire_creation(FormulaireBase, forms.Form):
    format = forms.ChoiceField(label="Format", choices=CHOIX_FORMAT_EXPORT_TRESOR, required=True)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Recherche le dernier format utilisé
        lot = PesModele.objects.last()
        if lot:
            self.fields["format"].initial = lot.format

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection du format",
                Field("format"),
            ),
        )


class Formulaire(FormulaireBase, ModelForm):
    modele_document = forms.ModelChoiceField(label="Modèle de facture", queryset=ModeleDocument.objects.filter(categorie="facture").order_by("nom"), required=False)

    class Meta:
        model = PesModele
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        format = kwargs.pop("format", None)
        if kwargs.get("instance", None):
            format = kwargs["instance"].format
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'lots_pes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Format
        self.fields["format"].disabled = True
        if not self.instance.pk:
            self.fields["format"].initial = format

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_pes_liste' %}"),
            Fieldset("Généralités",
                Field("format"),
                Field("nom"),
                Field("observations"),
            ),
            Fieldset("Paramètres",
                Field("compte"),
                Field("id_collectivite", type=None if format in ("pes", "jvs") else "hidden"),
                Field("code_collectivite", type=None if format in ("pes", "magnus", "jvs") else "hidden"),
                Field("code_budget", type=None if format in ("pes", "magnus", "jvs") else "hidden"),
                Field("code_prodloc", type=None if format in ("pes", "magnus", "jvs") else "hidden"),
                Field("id_poste", type=None if format in ("pes", "magnus", "jvs") else "hidden"),
                Field("code_etab", type=None if format in ("pes",) else "hidden"),
                Field("operation", type=None if format in ("magnus",) else "hidden"),
                Field("fonction", type=None if format in ("magnus",) else "hidden"),
                Field("service1", type=None if format in ("magnus",) else "hidden"),
                Field("service2", type=None if format in ("magnus",) else "hidden"),
                Field("edition_asap", type=None if format in ("magnus",) else "hidden"),
                Field("type_pj", type=None if format in ("magnus",) else "hidden"),
                Field("nom_tribunal", type=None if format in ("magnus",) else "hidden"),
                Field("payable_internet", type=None if format in ("magnus",) else "hidden"),
                Field("inclure_detail", type=None if format in ("magnus",) else "hidden"),
                Field("inclure_pieces_jointes", type=None if format in ("magnus",) else "hidden"),
                Field("inclure_tiers_solidaires", type=None if format in ("magnus",) else "hidden"),
                Field("modele_document", type=None if format in ("magnus",) else "hidden"),
                Field("code_compta_as_alias", type=None if format in ("magnus",) else "hidden"),
                Field("nom_collectivite", type=None if format in ("jvs",) else "hidden"),
            ),
            Fieldset("Libellés",
                Field("objet_piece"),
                Field("prestation_libelle"),
                Field("prelevement_libelle"),
            ),
            Fieldset("Règlement automatique",
                Field("reglement_auto"),
                Field("mode"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        format = self.cleaned_data["format"]

        if not self.cleaned_data["id_collectivite"] and format in ("pes", "jvs"):
            self.add_error("id_collectivite", "Vous devez renseigner l'identifiant de la collectivité")

        if not self.cleaned_data["code_collectivite"] and format in ("magnus", "pes", "jvs"):
            self.add_error("code_collectivite", "Vous devez renseigner le code collectivité")

        if not self.cleaned_data["code_budget"] and format in ("magnus", "pes", "jvs"):
            self.add_error("code_budget", "Vous devez renseigner le code budget")

        if not self.cleaned_data["id_poste"] and format in ("magnus", "pes", "jvs"):
            self.add_error("id_poste", "Vous devez renseigner le poste")

        if not self.cleaned_data["code_prodloc"] and format in ("magnus", "pes", "jvs"):
            self.add_error("code_prodloc", "Vous devez renseigner le code produit local")

        if not self.cleaned_data["code_etab"] and format in ("pes",):
            self.add_error("code_prodloc", "Vous devez renseigner le code produit local")

        if not self.cleaned_data["modele_document"] and format in ("magnus",) and self.cleaned_data["inclure_pieces_jointes"]:
            self.add_error("modele_document", "Vous devez sélectionner un modèle de facture")

        if not self.cleaned_data["nom_collectivite"] and format in ("jvs",):
            self.add_error("code_prodloc", "Vous devez renseigner le nom de la collectivité")

        return self.cleaned_data

EXTRA_SCRIPT = """
<script>

// Règlement automatique
function On_change_reglement_auto() {
    $('#div_id_mode').hide();
    if ($(this).prop("checked")) {
        $('#div_id_mode').show();
    }
}
$(document).ready(function() {
    $('#id_reglement_auto').change(On_change_reglement_auto);
    On_change_reglement_auto.call($('#id_reglement_auto').get(0));
});

</script>
"""
