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
from core.forms.select2 import Select2Widget
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Attestation, ModeleDocument
from core.widgets import DatePickerWidget, DateRangePickerWidget, FormIntegreWidget
from core.utils import utils_dates
from facturation.forms.attestations_options_impression import Formulaire as Form_options_impression
from fiche_famille.widgets import Prestations_devis


class Formulaire(FormulaireBase, ModelForm):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(), help_text="Sélectionnez la période à inclure dans l'attestation.")
    date_edition = forms.DateField(label="Date d'édition", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}), help_text="La date d'édition est par défaut la date du jour. Il est généralement inutile de la modifier.")
    numero = forms.IntegerField(label="Numéro", required=True, help_text="Le numéro de l'attestation est généré automatiquement. Il est généralement inutile de le modifier.")
    modele = forms.ModelChoiceField(label="Modèle de document", widget=Select2Widget(), queryset=ModeleDocument.objects.filter(categorie="attestation").order_by("nom"), required=True, help_text="Sélectionnez le modèle de document à utiliser. Il doit avoir au préalable été créé dans Menu Paramétrage > Modèles de documents > Attestation.")
    signataire = forms.CharField(label="Signataire", required=True, help_text="Saisissez le nom du signataire du document (par défaut l'utilisateur en cours).")
    options_impression = forms.CharField(label="Options d'impression", required=False, widget=FormIntegreWidget())
    prestations = forms.CharField(label="Prestations", required=False, widget=Prestations_devis(
        attrs={"texte_si_vide": "Aucune prestation", "hauteur_libre": True, "coche_tout": False}), help_text="Cochez les types de prestations à inclure dans l'attestation.")

    class Meta:
        model = Attestation
        fields = ["famille", "numero"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        utilisateur = kwargs.pop("utilisateur", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_devis_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date d'édition
        self.fields["date_edition"].initial = datetime.date.today()

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
            self.fields["periode"].initial = "%s - %s" % (utils_dates.ConvertDateToFR(self.instance.date_debut), utils_dates.ConvertDateToFR(self.instance.date_fin))
            self.fields["prestations"].initial = self.instance.prestations

        # Options : Ajoute le request au form
        self.fields['options_impression'].widget.attrs.update({"form": Form_options_impression(request=self.request)})

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_attestations_liste' idfamille=idfamille %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""<button class='btn btn-primary' onclick="impression_pdf(false, false)"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """)
                ],
                autres_commandes=[
                    HTML("""<a type='button' class='btn btn-default' title="Envoyer par Email" onclick="impression_pdf(true, false)" href='javascript:void(0)'><i class="fa fa-send-o margin-r-5"></i>Envoyer par email</a> """),
                    HTML("""<a type='button' class='btn btn-default' title="Aperçu PDF" href='javascript:void(0)' onclick="impression_pdf(false, true)"><i class="fa fa-file-pdf-o margin-r-5"></i>Aperçu PDF</a> """),
                ]),
            Hidden('famille', value=idfamille),
            Hidden('infos', value=""),
            Hidden("prestations_defaut", value=self.fields["prestations"].initial or ""),
            Field("periode"),
            Field("prestations"),
            Field("date_edition"),
            Field("numero"),
            Field("modele"),
            Field("signataire"),
            Field("options_impression"),
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


class Formulaire_prestations(FormulaireBase, forms.Form):
    prestations = forms.CharField(label="Prestations", required=False, widget=Prestations_devis(
        attrs={"texte_si_vide": "Aucune prestation", "hauteur_libre": True, "coche_tout": True}),
        help_text="Cochez les types de prestations à inclure dans l'attestation.")

    def __init__(self, *args, **kwargs):
        prestations = kwargs.pop("prestations", {})
        selections = kwargs.pop("selections", {})
        super(Formulaire_prestations, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_devis_prestations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.fields["prestations"].widget.attrs.update({"prestations": prestations, "selections": selections})
        if selections:
            self.fields["prestations"].widget.attrs.update({"coche_tout": False})

        # Affichage
        self.helper.layout = Layout(
            Field("prestations"),
        )
