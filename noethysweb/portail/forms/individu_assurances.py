# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.contrib import messages
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.models import Assurance, PortailRenseignement, Assureur
from core.widgets import DatePickerWidget, Select_avec_commandes_form
from portail.forms.fiche import FormulaireBase
from core.utils.utils_commandes import Commandes


class Form_choix_assureur(forms.ModelChoiceField):
    search_fields = ['nom__icontains', 'ville_resid__icontains']

    def label_from_instance(self, instance):
        return instance.Get_nom(afficher_ville=True)

class Formulaire(FormulaireBase, ModelForm):
    assureur = Form_choix_assureur(label="Assureur", queryset=Assureur.objects.all().order_by("nom"), required=True, help_text="Cliquez sur le champ ci-dessus pour sélectionner un assureur dans la liste déroulante. Vous pouvez faire une recherche par nom ou par ville.  <a href='#' class='ajouter_element'>Cliquez ici pour ajouter un assureur manquant dans la liste de choix.</a>",
                                     widget=Select_avec_commandes_form(attrs={"url_ajax": "portail_ajax_ajouter_assureur", "id_form": "assureurs_form", "afficher_bouton_ajouter": False,
                                                                              "textes": {"champ": "Nom de l'assureur", "ajouter": "Ajouter un assureur", "modifier": "Modifier un assureur"}}))

    class Meta:
        model = Assurance
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }
        help_texts = {
            "assureur": "Sélectionnez un assureur dans la liste proposée.",
            "num_contrat": "Saisissez le numéro de contrat.",
            "date_debut": "Saisissez la date de début d'effet du contrat.",
            "date_fin": "[Optionnel] Saisissez la date de fin du contrat.",
            "document": "Vous pouvez ajouter l'attestation d'assurance au format PDF ou image.",
        }

    def __init__(self, *args, **kwargs):
        rattachement = kwargs.pop("rattachement", None)
        mode = kwargs.pop("mode", "MODIFICATION")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_contacts_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # self.helper.use_custom_control = False

        # Date de début
        self.fields["date_debut"].initial = datetime.date.today()

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=rattachement.famille_id),
            Hidden('individu', value=rattachement.individu_id),
            Field("assureur"),
            Field("num_contrat"),
            Field("date_debut"),
            Field("date_fin"),
            Field("document"),
            Commandes(annuler_url="{% url 'portail_individu_assurances' idrattachement=rattachement.pk %}", aide=False, ajouter=False, css_class="pull-right"),
        )

    def clean(self):
        if "assureur" not in self.cleaned_data:
            messages.add_message(self.request, messages.ERROR, "Vous devez sélectionner un assureur dans la liste déroulante")

        if self.cleaned_data["date_fin"] and self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            messages.add_message(self.request, messages.ERROR, "La date de fin doit être supérieure à la date de début")
            self.add_error("date_fin", "La date de fin doit être supérieure à la date de début")

        return self.cleaned_data
