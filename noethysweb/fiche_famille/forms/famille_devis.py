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
from core.forms.base import FormulaireBase
from core.forms.select2 import Select2Widget, Select2MultipleWidget
from core.utils.utils_commandes import Commandes
from core.utils import utils_dates
from core.models import Devis, ModeleDocument
from core.widgets import DatePickerWidget, DateRangePickerWidget, FormIntegreWidget
from facturation.forms.devis_options_impression import Formulaire as Form_options_impression
from fiche_famille.widgets import Prestations_devis


class Formulaire(FormulaireBase, ModelForm):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(), help_text="Sélectionnez la période à inclure dans le devis.")
    date_edition = forms.DateField(label="Date d'édition", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}), help_text="La date d'édition est par défaut la date du jour. Il est généralement inutile de la modifier.")
    numero = forms.IntegerField(label="Numéro", required=True, help_text="Le numéro du devis est généré automatiquement. Il est généralement inutile de le modifier.")
    modele = forms.ModelChoiceField(label="Modèle de document", widget=Select2Widget(), queryset=ModeleDocument.objects.filter(categorie="devis").order_by("nom"), required=True, help_text="Sélectionnez le modèle de document à utiliser. Il doit avoir au préalable été créé dans Menu Paramétrage > Modèles de documents > Devis.")
    options_impression = forms.CharField(label="Options d'impression", required=False, widget=FormIntegreWidget())
    choix_categories = [("consommation", "Consommations"), ("cotisation", "Adhésions"), ("location", "Locations"), ("autre", "Autres"), ]
    categories = forms.MultipleChoiceField(label="Catégories de prestations", widget=Select2MultipleWidget(), choices=choix_categories, required=True, help_text="Cochez les catégories de prestations à inclure dans le devis.")
    prestations = forms.CharField(label="Prestations", required=False, widget=Prestations_devis(
        attrs={"texte_si_vide": "Aucune prestation", "hauteur_libre": True, "coche_tout": False}), help_text="Cochez les types de prestations à inclure dans le devis.")

    class Meta:
        model = Devis
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
        if not self.instance.iddevis:
            dernier_devis = Devis.objects.last()
            if dernier_devis:
                self.fields["numero"].initial = dernier_devis.numero + 1

        # Charge le modèle de document par défaut
        modele_defaut = ModeleDocument.objects.filter(categorie="devis", defaut=True)
        if modele_defaut:
            self.fields["modele"].initial = modele_defaut.first()

        # Si modification de devis
        if self.instance.iddevis:
            self.fields["numero"].initial = self.instance.numero
            self.fields["date_edition"].initial = self.instance.date_edition
            self.fields["periode"].initial = "%s - %s" % (utils_dates.ConvertDateToFR(self.instance.date_debut), utils_dates.ConvertDateToFR(self.instance.date_fin))
            self.fields["prestations"].initial = self.instance.prestations

        # Catégories
        self.fields["categories"].initial = ["consommation", "cotisation", "location", "autre"]

        # Options : Ajoute le request au form
        self.fields['options_impression'].widget.attrs.update({"form": Form_options_impression(request=self.request)})

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_devis_liste' idfamille=idfamille %}", enregistrer=False, ajouter=False,
                commandes_principales=[
                    HTML("""<button class='btn btn-primary' onclick="$('#famille_devis_form').submit()"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """)
                ],
                autres_commandes=[
                    HTML("""<a type="button" href="javascript:void(0)" class='btn btn-default' title="Envoyer par Email" onclick="impression_pdf(true, false)"><i class="fa fa-send-o margin-r-5"></i>Envoyer par email</a> """),
                    HTML("""<a type="button" href="javascript:void(0)" class='btn btn-default' title="Aperçu PDF" onclick="impression_pdf(false, true)"><i class="fa fa-file-pdf-o margin-r-5"></i>Aperçu PDF</a> """),
                ]),
            Hidden("famille", value=idfamille),
            Hidden("infos", value=""),
            Hidden("prestations_defaut", value=self.fields["prestations"].initial or ""),
            Field("periode"),
            Field("categories"),
            Field("prestations"),
            Field("date_edition"),
            Field("numero"),
            Field("modele"),
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
        help_text="Cochez les types de prestations à inclure dans le devis.")

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
