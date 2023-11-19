# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Attestation, ModeleDocument, Inscription
from core.widgets import DatePickerWidget, DateRangePickerWidget, FormIntegreWidget
from core.utils import utils_dates
from facturation.forms.attestations_options_impression import Formulaire as Form_options_impression


class Formulaire(FormulaireBase, ModelForm):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())
    date_edition = forms.DateField(label="Date d'édition", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}), help_text="Par défaut la date du jour. Modifiez uniquement si nécessaire.")
    individus = forms.MultipleChoiceField(label="Individus", widget=Select2MultipleWidget(), choices=[], required=True)
    activites = forms.MultipleChoiceField(label="Activités", widget=Select2MultipleWidget(), choices=[], required=True)
    numero = forms.IntegerField(label="Numéro", required=True, help_text="Ce numéro est attribué par défaut. Modifiez uniquement si nécessaire.")
    modele = forms.ModelChoiceField(label="Modèle de document", widget=Select2Widget(), queryset=ModeleDocument.objects.filter(categorie="attestation").order_by("nom"), required=True)
    signataire = forms.CharField(label="Signataire", required=True, help_text="Saisissez le nom du signataire du document (par défaut l'utilisateur en cours).")
    options_impression = forms.CharField(label="Options d'impression", required=False, widget=FormIntegreWidget())

    class Meta:
        model = Attestation
        fields = ["famille", "numero", "filtre_prestations", "exclusions_prestations"]
        help_texts = {
            "filtre_prestations": "Si vous souhaitez uniquement certaines prestations, tapez leur nom ou une partie de leur nom, séparées par des points-virgules (;). Exemple : journées avec repas;piscine;matin.",
            "exclusions_prestations": "Si vous souhaitez exclure certaines prestations, tapez leur nom ou une partie de leur nom, séparées par des points-virgules (;). Exemple : journées avec repas;piscine;matin.",
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        utilisateur = kwargs.pop("utilisateur", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_attestations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date d'édition
        self.fields["date_edition"].initial = datetime.date.today()

        # Recherche les inscriptions de la famille
        inscriptions = Inscription.objects.select_related("activite", "activite__structure", "individu").filter(famille_id=idfamille, activite__structure__in=utilisateur.structures.all())

        # Individus
        liste_individus = list({(inscription.individu_id, inscription.individu.prenom): None for inscription in inscriptions}.keys())
        self.fields["individus"].choices = liste_individus
        self.fields["individus"].initial = [id for id, nom in liste_individus]

        # Activités
        liste_activites = list({(inscription.activite_id, inscription.activite.nom): None for inscription in inscriptions}.keys())
        self.fields["activites"].choices = liste_activites
        self.fields["activites"].initial = [id for id, nom in liste_activites]

        # Numéro
        self.fields["numero"].initial = 1
        if not self.instance.idattestation:
            derniere_attestation = Attestation.objects.last()
            if derniere_attestation:
                self.fields["numero"].initial = derniere_attestation.numero + 1

        # Signataire
        if utilisateur:
            self.fields["signataire"].initial = utilisateur.get_full_name() or utilisateur.get_short_name() or utilisateur

        # Charge le modèle de document par défaut
        modele_defaut = ModeleDocument.objects.filter(categorie="attestation", defaut=True)
        if modele_defaut:
            self.fields["modele"].initial = modele_defaut.first()

        # Si modification d'attestation
        if self.instance.idattestation:
            self.fields["numero"].initial = self.instance.numero
            self.fields["date_edition"].initial = self.instance.date_edition
            self.fields["individus"].initial = [int(idindividu) for idindividu in self.instance.individus.split(";")] if self.instance.individus else []
            self.fields["activites"].initial = [int(idindividu) for idindividu in self.instance.activites.split(";")] if self.instance.activites else []
            self.fields["periode"].initial = "%s - %s" % (utils_dates.ConvertDateToFR(self.instance.date_debut), utils_dates.ConvertDateToFR(self.instance.date_fin))

        # Options : Ajoute le request au form
        self.fields['options_impression'].widget.attrs.update({"form": Form_options_impression(request=self.request)})

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_attestations_liste' idfamille=idfamille %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""<button class='btn btn-primary' onclick="impression_pdf(false, false)"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """)
                ],
                autres_commandes=[
                    HTML("""<a type='button' class='btn btn-default' title="Envoyer par Email" onclick="impression_pdf(true, false)" href='#'><i class="fa fa-send-o margin-r-5"></i>Envoyer par email</a> """),
                    HTML("""<a type='button' class='btn btn-default' title="Aperçu PDF" href='#' onclick="impression_pdf(false, true)"><i class="fa fa-file-pdf-o margin-r-5"></i>Aperçu PDF</a> """),
                ]),
            Hidden('famille', value=idfamille),
            Hidden('infos', value=""),
            Field("periode"),
            Field("date_edition"),
            Field("individus"),
            Field("activites"),
            Field("filtre_prestations"),
            Field("exclusions_prestations"),
            Field("numero"),
            Field("modele"),
            Field("signataire"),
            Field("options_impression"),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        if self.data.get("infos"):
            self.cleaned_data["infos"] = json.loads(self.data.get("infos"))

        # Vérification du formulaire des options d'impression
        form_options = Form_options_impression(self.data, request=self.request)
        if not form_options.is_valid():
            liste_erreurs = form_options.errors.as_data().keys()
            self.add_error("options_impression", "Veuillez renseigner les champs manquants : %s." % ", ".join(liste_erreurs))

        # Rajoute les options d'impression formatées aux résultats du formulaire
        self.cleaned_data["options_impression"] = form_options.cleaned_data
        return self.cleaned_data


EXTRA_HTML = """

{# Insertion des modals #}
{% include 'outils/modal_editeur_emails.html' %}
{% include 'core/modal_pdf.html' %}
{% load static %}

<script>

// Impression du PDF
function impression_pdf(email=false, afficher=true) {
    $.ajax({
        type: "POST",
        url: "{% url 'ajax_attestation_impression_pdf' %}",
        data: $("#famille_attestations_form").serialize(),
        datatype: "json",
        success: function(data){
            $('input[name=infos]').val(JSON.stringify(data.infos));
            if (email) {
                envoyer_email(data)
            } 
            if (afficher) {
                charge_pdf(data);
            }
            if ((email === false) & (afficher == false)) {
                $("#famille_attestations_form").submit()
            };
        },
        error: function(data) {
            toastr.error(data.responseJSON.erreur);
        }
    })
};

</script>

"""
