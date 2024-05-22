# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.forms.select2 import Select2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Activite, Groupe
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
    date_application = forms.DateField(label="Date d'application", required=True, widget=DatePickerWidget(), help_text="Renseignez la date d'application. Les nouvelles inscriptions débuteront à cette date.")
    groupe = forms.ModelChoiceField(label="Nouveau groupe", queryset=Groupe.objects.none(), required=True, help_text="Sélectionnez le nouveau groupe à appliquer.")

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite", None)
        super(Formulaire_options, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'options_inscription'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Groupe
        self.fields['groupe'].queryset = Groupe.objects.filter(activite_id=idactivite).order_by("ordre")
        if len(self.fields['groupe'].queryset) == 1:
            # S'il n'y a qu'un groupe, on le sélectionne par défaut
            self.fields['groupe'].initial = self.fields['groupe'].queryset.first()

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Nouveaux paramètres de l'inscription",
                Field("date_application"),
                Field("groupe"),
            ),
            Fieldset("Sélection des inscriptions à modifier"),
        )

    def clean(self):
        return self.cleaned_data
