# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Div, Fieldset
from crispy_forms.bootstrap import Field, InlineRadios
from django_select2.forms import ModelSelect2Widget
from core.utils.utils_commandes import Commandes
from core.models import Individu, Rattachement, CATEGORIES_RATTACHEMENT
from core.forms.base import FormulaireBase
from fiche_famille.utils import utils_doublons


class Formulaire(FormulaireBase, ModelForm):
    action = forms.ChoiceField(label="Action*", widget=forms.RadioSelect, choices=[("CREER", "Créer un individu"), ("RATTACHER", "Rattacher un individu existant")], required=False)
    categorie = forms.ChoiceField(label="Catégorie*", widget=forms.RadioSelect, choices=CATEGORIES_RATTACHEMENT, required=False)
    titulaire = forms.BooleanField(label="Titulaire du dossier", initial=True, required=False)
    nom = forms.CharField(label="Nom*", required=False, help_text="Saisissez le nom de famille en majuscules. Ex : DUPOND.")
    prenom = forms.CharField(label="Prénom*", required=False, help_text="Saisissez le prénom en minuscules avec la première lettre en majuscule. Ex : Kévin.")
    confirmation_doublon = forms.BooleanField(label="Je confirme qu'il s'agit d'une personne différente des individus signalés ci-dessus", required=False)
    individu = forms.ModelChoiceField(
        label="Individu*", queryset=Individu.objects.all().order_by("nom", "prenom"),
        widget=ModelSelect2Widget(model=Individu, search_fields=["nom__icontains", "prenom__icontains"], attrs={"data-minimum-input-length": 0}), required=False,
    )

    class Meta:
        model = Individu
        fields = ["civilite", "nom", "prenom"]
        help_texts = {
            "civilite": "Sélectionnez une civilité dans la liste. S'il s'agit d'un enfant, sélectionnez Fille ou Garçon.",
        }

    def __init__(self, *args, **kwargs):
        if "idfamille" in kwargs:
            self.idfamille = kwargs.pop("idfamille")
            self.creer_famille = False
        else:
            self.idfamille = 0
            self.creer_famille = True

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_ajouter_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Action
        self.fields['action'].initial = "CREER"

        # Récupération des rattachements existants
        rattachements = Rattachement.objects.filter(famille_id=self.idfamille)

        # Récupération du nom de famille d'un des titulaires
        for rattachement in rattachements:
            if rattachement.categorie == 1 and rattachement.titulaire:
                self.fields['nom'].initial = rattachement.individu.nom
                break

        # Si on saisit le premier individu de la fiche famille
        if not rattachements:
            self.fields['categorie'].initial = 1
            self.fields['categorie'].widget.attrs['disabled'] = 'disabled'
            self.fields['titulaire'].disabled = True

        # Désactive l'autocomplete
        self.fields['nom'].widget.attrs.update({'autocomplete': 'off'})
        self.fields['prenom'].widget.attrs.update({'autocomplete': 'off'})

        # Affichage
        self.helper.layout = Layout(
            Hidden('idfamille', value=self.idfamille),
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False,
                      annuler_url="{% url 'famille_liste' %}" if self.creer_famille else "{% url 'famille_resume' idfamille=idfamille %}"
                      ),
            Fieldset("Action",
                InlineRadios('action')
            ),
            Fieldset("Catégorie",
                InlineRadios('categorie'),
                Field('titulaire'),
            ),
            Fieldset("Identité",
                Div(
                    Field("civilite"),
                    Field('nom'),
                    Field('prenom'),
                    HTML('<div id="individus_suggestions"></div>'),
                    Div(Field('confirmation_doublon'), id="div_confirmation_doublon", css_class="doublons-confirmation"),
                    id="saisie_identite",
                ),
                Div(
                    Field('individu'),
                    id="selection_identite",
                ),
            ),
            HTML(EXTRA_SCRIPT),
        )

    # def Creer_bouton_annuler(self):
    #     if self.creer_famille:
    #         return """<a class="btn btn-danger" href="{% url 'famille_liste' %}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""
    #     else:
    #         return """<a class="btn btn-danger" href="{% url 'famille_resume' idfamille=idfamille %}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""

    def clean(self):
        # Catégorie
        if "disabled" in self.fields['categorie'].widget.attrs:
            self.cleaned_data["categorie"] = 1

        if self.cleaned_data["categorie"] == "":
            self.add_error("categorie", "Vous devez sélectionner une catégorie")
            return

        # Titulaire
        if self.cleaned_data["categorie"] in ('2', '3'):
            self.cleaned_data["titulaire"] = False

        # Action CREER
        if self.cleaned_data["action"] == "CREER":

            # Nom
            if self.cleaned_data["nom"] in (None, ""):
                self.add_error("nom", "Vous devez saisir un nom")
                return

            # Prénom
            if self.cleaned_data["civilite"] < 6 and self.cleaned_data["prenom"] in (None, ""):
                self.add_error("prenom", "Vous devez saisir un prénom")
                return

            # Doublon très probable : confirmation obligatoire
            doublons = utils_doublons.Rechercher_doublons(nom=self.cleaned_data["nom"], prenom=self.cleaned_data["prenom"],
                                                          sans_prenom=self.cleaned_data["civilite"] >= 6, idfamille=self.idfamille)
            tres_probables = ["%s (ID%d)" % (doublon["individu"].Get_nom(), doublon["individu"].pk) for doublon in doublons if doublon["niveau"] == 3]
            membres = ["%s (ID%d)" % (doublon["individu"].Get_nom(), doublon["individu"].pk) for doublon in doublons if doublon["niveau"] == 3 and doublon["deja_membre"]]
            if tres_probables:
                if not self.cleaned_data.get("confirmation_doublon"):
                    if membres:
                        message = "%s fait déjà partie de cette famille. Cochez cette case uniquement s'il s'agit d'une autre personne." % ", ".join(membres)
                    else:
                        message = "Un individu très ressemblant existe déjà : %s. Rattachez-le plutôt à la famille ou, s'il s'agit d'une autre personne, cochez cette case pour confirmer la création." % ", ".join(tres_probables)
                    self.add_error("confirmation_doublon", message)
                    return
                self.doublons_ignores = tres_probables

        # Action RATTACHER
        if self.cleaned_data["action"] == "RATTACHER":

            # Sélection individu
            if self.cleaned_data["individu"] == None:
                self.add_error("individu", "Vous devez sélectionner un individu dans la liste")
                return

            # Vérifie que l'individu n'est pas déjà rattaché à cette famille
            rattachement = Rattachement.objects.filter(individu=self.cleaned_data["individu"], famille_id=self.idfamille)
            if rattachement.exists():
                self.add_error("individu", "Cet individu est déjà rattaché à cette famille")
                return

        return self.cleaned_data



EXTRA_SCRIPT = """

<style>

.doublons-panneau { border: 1px solid #f0ad4e; border-radius: 4px; margin: 0 0 15px 0; }
.doublons-entete { background-color: #fcf8e3; color: #8a6d3b; padding: 6px 10px; font-weight: bold; }
.dark-mode .doublons-entete { background-color: #5c4a1e; color: #fff3cd; }
.doublons-ligne { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 6px 10px; border-top: 1px solid #eee; }
.dark-mode .doublons-ligne { border-top-color: #555; }
.doublons-identite { flex: 1; min-width: 220px; }
.doublons-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.doublons-niveau-3 { background-color: #dc3545; color: #fff; }
.doublons-niveau-2 { background-color: #ffc107; color: #212529; }
.doublons-niveau-1 { background-color: #e9ecef; color: #495057; }
.doublons-confirmation { display: none; border: 1px solid #dc3545; border-radius: 4px; padding: 8px 10px 0 10px; margin-bottom: 15px; }

.radio-inline {
    padding-left: 0px;
}
.iradio_minimal-blue {
    margin-right: 5px;
}

</style>

<script>

{% include 'core/csrftoken.html' %}

// Action
function On_change_action() {
    $('#saisie_identite').hide();
    $('#selection_identite').hide();
    if ($(this).prop("checked") && this.value == 'CREER') {
        $('#saisie_identite').show();
    };
    if ($(this).prop("checked") && this.value == 'RATTACHER') {
        $('#selection_identite').show();
    };
    if ($(this).prop("checked") == false && this.value == 'CREER') {
        $('#selection_identite').show();
    };
}
$(document).ready(function() {
    $('input[type=radio][name=action]').on('change', On_change_action);
    On_change_action.call($('input[type=radio][name=action]').get(0));
});


// Catégorie
function On_change_categorie() {
    $('#div_id_titulaire').hide();
    if ($(this).prop("checked") && this.value == 1) {
        $('#div_id_titulaire').show();
    }
}
$(document).ready(function() {
    $('input[type=radio][name=categorie]').on('change', On_change_categorie);
    On_change_categorie.call($('input[type=radio][name=categorie]').get(0));
});

// Civilité
function On_change_civilite() {
    $('#div_id_prenom').hide();
    if($(this).val() < 6) {
        $('#div_id_prenom').show();
    }
}
$(document).ready(function() {
    $('#id_civilite').change(On_change_civilite);
    On_change_civilite.call($('#id_civilite').get(0));
});


// Recherche des doublons (temporisée, la requête précédente est annulée)
var requete_doublons = null, minuteur_doublons = null;
function Rechercher_doublons() {
    if (requete_doublons) {requete_doublons.abort();}
    requete_doublons = $.ajax({
        type: "POST",
        url: "{% url 'ajax_get_individus_existants' %}",
        data: {'nom': $('#id_nom').val(), 'prenom': $('#id_prenom').val(), 'civilite': $('#id_civilite').val(), 'idfamille': $('input[name=idfamille]').val()},
        success: function(data) {
            $("#individus_suggestions").html(data);
            var tres_probable = $("#individus_suggestions .doublons-panneau").data("tres-probable") == 1;
            $("#div_confirmation_doublon").toggle(tres_probable || $("#div_confirmation_doublon .invalid-feedback, #div_confirmation_doublon .is-invalid").length > 0);
        },
    });
}
function On_change_nom(e) {
    // Une nouvelle saisie annule une confirmation donnée pour un autre nom
    if (e) {$("#id_confirmation_doublon").prop("checked", false);}
    clearTimeout(minuteur_doublons);
    minuteur_doublons = setTimeout(Rechercher_doublons, 300);
}
$(document).ready(function() {
    $('#id_nom, #id_prenom').on('input', On_change_nom);
    $('#id_civilite').on('change', On_change_nom);
    if ($("#div_confirmation_doublon .invalid-feedback, #div_confirmation_doublon .is-invalid").length) {$("#div_confirmation_doublon").show();}
    Rechercher_doublons();

    // Rattacher directement un individu existant proposé
    $(document).on("click", ".bouton_rattacher_doublon", function() {
        $("input[type=radio][name=action][value=RATTACHER]").prop("checked", true).trigger("change");
        var option = new Option($(this).data("label"), $(this).data("id"), true, true);
        $("#id_individu").empty().append(option).trigger("change");
        $("#id_individu").closest(".form-group").get(0).scrollIntoView({behavior: "smooth", block: "center"});
    });
});


</script>


"""