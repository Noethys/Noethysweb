# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, HTML, Div
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils import utils_texte
from core.models import Mandat, Famille, Rattachement
from core.widgets import DatePickerWidget, CodePostal, Ville, Rue
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from facturation.widgets import ChampAutomatiqueWidget
from facturation.utils import utils_prelevements


class Formulaire(FormulaireBase, ModelForm):
    type_structures = forms.ChoiceField(label="Structures associées", choices=[("TOUTES", "Toutes les structures"), ("SELECTION", "Uniquement les structures suivantes")], initial="TOUTES", required=False)

    class Meta:
        model = Mandat
        fields = "__all__"
        widgets = {
            "date": DatePickerWidget(),
            "individu_rue": Rue(attrs={"id_codepostal": "id_individu_cp", "id_ville": "id_individu_ville"}),
            "individu_cp": CodePostal(attrs={"id_ville": "id_individu_ville"}),
            "individu_ville": Ville(attrs={"id_codepostal": "id_individu_cp"}),
            "memo": forms.Textarea(attrs={"rows": 3}),
            "rum": ChampAutomatiqueWidget(attrs={"label_checkbox": "Automatique", "title": "Saisissez un numéro unique"}),
            "structures": Select2MultipleWidget(),
        }
        labels = {
            "structures": "Sélection des structures",
        }
        help_texts = {
            "individu": "Titulaire du compte bancaire. Sélectionnez 'Autre individu' si le titulaire n'est pas dans la liste proposée ou si vous souhaitez saisir une adresse postale manuellement.",
            "individu_nom": "Saisissez le nom complet du titulaire du compte (Généralement le nom de famille suivi du prénom). Exemple : DUPOND Philippe.",
            "individu_service": "Identité du destinataire ou du service. Exemple : Service comptabilité.",
            "individu_rue": "Libellé de la voie sans le numéro. Exemple : Rue des alouettes.",
            "individu_numero": "Numéro de la voie. Exemple : 14.",
            "individu_batiment": "Nom de l'immeuble, du bâtiment ou de la résidence, etc... Exemple : Résidence les acacias.",
            "individu_etage": "Numéro de l'étage, de l'annexe, etc... Exemple : Etage 4.",
            "individu_boite": "Boîte postale, tri service arrivée, etc... Exemple : BP64.",
            "individu_cp": "Code postal. Exemple : 29200.",
            "individu_ville": "Nom de la ville. Exemple : BREST.",
            "individu_pays": "Code du pays. Exemple : FR.",
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille", None)
        if kwargs.get("instance", None):
            idfamille = kwargs["instance"].famille_id
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "liste_mandats_form"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Titulaire du compte
        rattachements = Rattachement.objects.select_related("individu").filter(famille_id=idfamille, categorie=1).order_by("individu__nom", "individu__prenom")
        self.fields["individu"].choices = [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements] + [(None, "Autre individu")]

        # Valeurs par défaut si création
        if not self.instance.pk:
            # Insérer date du jour
            self.fields["date"].initial = datetime.date.today()

            # Insérer le prochain RUM
            dernier_mandat = Mandat.objects.last()
            dernier_rum = dernier_mandat.rum if dernier_mandat else 0
            self.fields["rum"].initial = utils_texte.Incrementer(str(dernier_rum))

            # Titulaire du compte
            self.fields["individu"].initial = rattachements.first().individu_id

        # Structures
        if self.instance.pk and self.instance.structures.all():
            self.fields["type_structures"].initial = "SELECTION"

        # Bouton Annuler
        if self.mode == "fiche_famille":
            annuler_url = "{% url 'famille_mandats_liste' idfamille=idfamille %}"
        else:
            annuler_url = "{% url 'mandats_liste' %}"

        # Affichage
        self.helper.layout = Layout(
            Hidden("famille", value=idfamille),
            Commandes(annuler_url=annuler_url),
            Fieldset("Généralités",
                Field("rum"),
                Field("date"),
                Field("type"),
                Field("actif"),
            ),
            Fieldset("Compte bancaire",
                Field("iban"),
                Field("bic"),),
            Fieldset("Titulaire du compte",
                Field("individu"),
                Div(
                    Field("individu_nom"),
                    Field("individu_service"),
                    Field("individu_numero"),
                    Field("individu_rue"),
                    Field("individu_batiment"),
                    Field("individu_etage"),
                    Field("individu_boite"),
                    Field("individu_cp"),
                    Field("individu_ville"),
                    Field("individu_pays"),
                    id="div_autre_individu",
                )
            ),
            Fieldset("Options",
                Field("type_structures"),
                Field("structures"),
                Field("sequence"),
                Field("memo"),
            ),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        # RUM
        for mandat in Mandat.objects.filter(rum=self.cleaned_data["rum"]):
            if mandat != self.instance:
                self.add_error("rum", "Ce numéro a déjà été attribué à la famille %s" % mandat.famille)

        # Individu
        if not self.cleaned_data["individu"]:
            if not self.cleaned_data["individu_nom"]:
                self.add_error("individu_nom", "Vous devez spécifier un nom pour le titulaire du compte")

        # IBAN
        if not utils_prelevements.CheckIBAN(self.cleaned_data["iban"]):
            self.add_error("iban", "Vous devez saisir un IBAN valide")

        # BIC
        if not utils_prelevements.CheckBIC(self.cleaned_data["bic"]):
            self.add_error("bic", "Vous devez saisir un BIC valide")

        # Actif
        if self.cleaned_data["actif"] and Mandat.objects.filter(famille=self.cleaned_data["famille"], actif=True).exclude(pk=self.instance.pk):
            self.add_error("actif", "Un autre mandat est déjà actif pour cette famille, vous devez donc le désactiver avant de pouvoir activer celui-ci.")

        # Structures
        if self.cleaned_data.get("type_structures") == "SELECTION" and not self.cleaned_data.get("structures"):
            self.add_error("structures", "Vous devez sélectionner au moins une structure dans la liste")
        if self.cleaned_data.get("type_structures") == "TOUTES":
            self.cleaned_data["structures"] = []

        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_individu() {
        $("#div_autre_individu").hide();
        if (!($("#id_individu").val())) {
            $("#div_autre_individu").show();
        };
    }
    $(document).ready(function() {
        $("#id_individu").change(On_change_individu);
        On_change_individu.call($("#id_individu").get(0));
    });
    
    function On_change_type_structures() {
        $("#div_id_structures").hide();
        if ($("#id_type_structures").val() == "SELECTION") {
            $("#div_id_structures").show();
        };
    }
    $(document).ready(function() {
        $("#id_type_structures").change(On_change_type_structures);
        On_change_type_structures.call($("#id_type_structures").get(0));
    });
</script>
"""


class Formulaire_creation(FormulaireBase, forms.Form):
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget({"lang": "fr", "data-width": "100%"}), queryset=Famille.objects.all().order_by("nom"), required=True)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance")
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection de la famille",
                Field("famille"),
            ),
        )
