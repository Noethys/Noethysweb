# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field, PrependedText
from core.widgets import DatePickerWidget
from core.models import Quotient
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Quotient
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 2}),
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        mode = kwargs.pop("mode", "MODIFICATION")
        self.famille = kwargs.pop("famille", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_quotients_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Hidden("famille", value=self.famille.pk),
            Fieldset(_("Quotient"),
                Field("date_debut"),
                Field("date_fin"),
                Field("type_quotient"),
                PrependedText("quotient", utils_preferences.Get_symbole_monnaie()),
                Field("observations"),
            ),
            Fieldset("Document numérisé",
                Field('document'),
            ),
            Commandes(annuler_url="{% url 'portail_famille_quotients' %}", aide=False, ajouter=False, css_class="pull-right"),
        )

    def clean(self):
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return
        return self.cleaned_data
