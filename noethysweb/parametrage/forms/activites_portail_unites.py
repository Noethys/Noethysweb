# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Div, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import PortailUnite, Unite, Activite
from django.db.models import Max
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    unites_principales = forms.ModelMultipleChoiceField(label="Unités principales", widget=Select2MultipleWidget(), queryset=Unite.objects.none(),
                                                        required=True, help_text="L'unité de réservation est affichée sur une date donnée uniquement si toutes les unités principales associées sont ouvertes.")
    unites_secondaires = forms.ModelMultipleChoiceField(label="Unités secondaires", widget=Select2MultipleWidget(), queryset=Unite.objects.none(),
                                                        required=False, help_text="Les unités secondaires ne conditionnent pas l'affichage de l'unité de réservation.")

    class Meta:
        model = PortailUnite
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_portail_unites_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Unités associées
        self.fields['unites_principales'].queryset = Unite.objects.filter(activite_id=idactivite)
        self.fields['unites_secondaires'].queryset = Unite.objects.filter(activite_id=idactivite)

        # Ordre
        if self.instance.ordre == None:
            max = PortailUnite.objects.filter(activite_id=idactivite).aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=idactivite),
            Hidden('ordre', value=self.fields['ordre'].initial),
            Fieldset("Généralités",
                Field("nom"),
            ),
            Fieldset("Caractéristiques",
                Field("unites_principales"),
                Field("unites_secondaires"),
            ),
        )
