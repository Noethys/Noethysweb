# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.utils import utils_dates
from core.forms.select2 import Select2MultipleWidget
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase
from core.models import AchatFournisseur


class Formulaire(FormulaireBase, forms.Form):
    fournisseurs = forms.ModelMultipleChoiceField(label="Fournisseurs", required=True, widget=Select2MultipleWidget({"data-minimum-input-length": 0}),
                                             queryset=AchatFournisseur.objects.none(), help_text="Sélectionnez un ou plusieurs fournisseurs.")
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(), help_text="Sélectionnez une période pour sélectionner les demandes selon la date d'échéance.")
    achete = forms.MultipleChoiceField(label="Acheté", required=True, widget=Select2MultipleWidget(), choices=[(True, "Oui"), (False, "Non")], initial=[False])
    orientation = forms.ChoiceField(label="Orientation de la page", choices=[("portrait", "Portrait"), ("paysage", "Paysage")], initial="portrait", required=False, help_text="Sélectionnez l'orientation de la page.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Fournisseurs
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        self.fields["fournisseurs"].queryset = AchatFournisseur.objects.filter(condition_structure).order_by("nom")

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'comptabilite_toc' %}", enregistrer=False, ajouter=False,
                commandes_principales=[HTML(
                    """<a type='button' class="btn btn-primary margin-r-5" onclick="generer_pdf()" title="Génération du PDF"><i class='fa fa-file-pdf-o margin-r-5'></i>Générer le PDF</a>"""),
                ]),
            Fieldset("Sélection des individus",
                Field("fournisseurs"),
                Field("periode"),
                Field("achete"),
            ),
            Fieldset("Options",
                Field("orientation"),
            ),
        )

    def clean(self):
        self.cleaned_data["periode"] = utils_dates.ConvertDateRangePicker(self.cleaned_data["periode"])
        return self.cleaned_data
