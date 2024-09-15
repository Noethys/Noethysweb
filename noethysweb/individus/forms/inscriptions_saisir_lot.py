# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Activite, Groupe, CategorieTarif
from core.widgets import DatePickerWidget, Select_activite


class Formulaire_activite(FormulaireBase, forms.Form):
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_activite, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection de l'activité",
                Field("activite"),
            ),
        )


class Formulaire_options(FormulaireBase, forms.Form):
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget(), help_text="Renseignez la date de début de l'inscription.")
    groupe = forms.ModelChoiceField(label="Groupe", queryset=Groupe.objects.none(), required=True, help_text="Sélectionnez le groupe à appliquer.")
    categorie_tarif = forms.ModelChoiceField(label="Catégorie de tarif", queryset=CategorieTarif.objects.none(), required=True, help_text="Sélectionnez la catégorie de tarif à appliquer.")

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite", None)
        super(Formulaire_options, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'options_inscription'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date
        self.fields["date_debut"].initial = datetime.date.today()

        # Groupe
        self.fields["groupe"].queryset = Groupe.objects.filter(activite_id=idactivite).order_by("ordre")
        if len(self.fields["groupe"].queryset) == 1:
            # S'il n'y a qu'un groupe, on le sélectionne par défaut
            self.fields["groupe"].initial = self.fields["groupe"].queryset.first()

        # Catégorie de tarif
        self.fields["categorie_tarif"].queryset = CategorieTarif.objects.filter(activite_id=idactivite).order_by("nom")
        if len(self.fields["categorie_tarif"].queryset) == 1:
            # S'il n'y a qu'une catégorie, on la sélectionne par défaut
            self.fields["categorie_tarif"].initial = self.fields["categorie_tarif"].queryset.first()

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Paramètres de l'inscription",
                Field("date_debut"),
                Field("groupe"),
                Field("categorie_tarif"),
            ),
            Fieldset("Sélection des individus à inscrire"),
        )

    def clean(self):
        return self.cleaned_data
