# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field, InlineRadios
from core.models import Individu
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):
    categorie = forms.ChoiceField(label="Catégorie", widget=forms.RadioSelect, choices=[(1, "Représentant"), (2, "Enfant")], required=True, help_text="Sélectionnez Représentant pour créer un adulte (Exemples : père, mère, conjoint, tuteur...) ou sélectionnez Enfant pour créer un enfant.")
    titulaire = forms.BooleanField(label="Est également titulaire du dossier", initial=True, required=False, help_text="Décochez cette case si cet adulte ne doit pas être considéré comme l'un des responsables du dossier.")
    civilite_representant = forms.ChoiceField(label="Civilité*", choices=[(1, "Monsieur"), (3, "Madame")], required=False, help_text="Sélectionnez une civilité dans la liste déroulante.")
    civilite_enfant = forms.ChoiceField(label="Sexe*", choices=[(4, "Garçon"), (5, "Fille")], required=False, help_text="Sélectionnez le sexe dans la liste déroulante.")
    nom = forms.CharField(label="Nom de famille", required=True, help_text="Saisissez votre nom de famille en majuscules. Ex : DUPOND.")
    prenom = forms.CharField(label="Prénom", required=True, help_text="Saisissez votre prénom en minuscules avec la première lettre en majuscule. Ex : Sophie.")

    class Meta:
        model = Individu
        fields = ["civilite", "nom", "prenom"]

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_creer_individu"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        self.fields["categorie"].initial = 1

        self.helper.layout = Layout(
            Field("civilite", type="hidden"),
            Field("categorie"),
            Field("titulaire"),
            Field("civilite_representant"),
            Field("civilite_enfant"),
            Field("nom"),
            Field("prenom"),
            HTML(EXTRA_SCRIPT),
            Commandes(
                enregistrer_label="<i class='fa fa-check margin-r-5'></i>%s" % _("Valider"),
                annuler_url="{% url 'portail_renseignements' %}", ajouter=False, aide=False, css_class="pull-right"),
        )
        self.Appliquer_version_bootstrap(5)

    def clean(self):
        # Formatage du nom et du prénom
        self.cleaned_data["nom"] = self.cleaned_data["nom"].upper()
        self.cleaned_data["prenom"] =  self.cleaned_data["prenom"].title()

        # Mémorise la civilité
        self.cleaned_data["civilite"] = self.cleaned_data["civilite_representant"] if self.cleaned_data["titulaire"] == 1 else self.cleaned_data["civilite_enfant"]

        # Vérifie que l'individu n'existe pas déjà dans la base
        if Individu.objects.filter(nom__iexact=self.cleaned_data["nom"], prenom__iexact=self.cleaned_data["prenom"]).exists():
            self.add_error("prenom", "Cette identité est déjà répertoriée, vous ne pouvez donc pas créer une nouvelle fiche à ce nom et à ce prénom. Contactez l'administrateur.")

        return self.cleaned_data


EXTRA_SCRIPT = """
<style>
    @media (min-width: 768px) {
        .col-md-2 {
            text-align: right;
        }
    }
</style>

<script>

    // Catégorie
    function On_change_categorie() {
        $('#div_id_titulaire').hide();
        $('#div_id_civilite_representant').hide();
        $('#div_id_civilite_enfant').hide();
        if ($(this).prop("checked") && this.value == 1) {
            $('#div_id_titulaire').show();
            $('#div_id_civilite_representant').show();
        } else {
            $('#div_id_civilite_enfant').show();
        }
    }
    $(document).ready(function() {
        $('input[type=radio][name=categorie]').on('change', On_change_categorie);
        On_change_categorie.call($('input[type=radio][name=categorie]').get(0));
    });

</script>
"""
