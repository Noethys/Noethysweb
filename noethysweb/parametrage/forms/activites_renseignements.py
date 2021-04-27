# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, PrependedText
from core.utils.utils_commandes import Commandes
from core.models import Activite, TypePiece, TypeCotisation
from django_select2.forms import Select2MultipleWidget

class Formulaire(ModelForm):
    # Pièces à fournir
    pieces = forms.ModelMultipleChoiceField(label="Pièces à fournir", widget=Select2MultipleWidget({"lang":"fr"}), queryset=TypePiece.objects.all(), required=False)

    # Cotisations à fournir
    cotisations = forms.ModelMultipleChoiceField(label="Adhésions à jour", widget=Select2MultipleWidget({"lang":"fr"}), queryset=TypeCotisation.objects.all(), required=False)

    class Meta:
        model = Activite
        fields = ["pieces", "cotisations", "vaccins_obligatoires"]

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_renseignements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(ajouter=False, annuler_url="{% url 'activites_resume' idactivite=activite.idactivite %}"),
            Fieldset("Pièces à fournir",
                Field("pieces"),
            ),
            Fieldset("Cotisations",
                Field("cotisations"),
            ),
            Fieldset("Vaccinations",
                Field("vaccins_obligatoires"),
            ),
        )

