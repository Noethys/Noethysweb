# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.models import TypeCotisation, Cotisation
from core.utils.utils_commandes import Commandes


class Formulaire(FormulaireBase, ModelForm):
    # Modification du label de la checkbox
    carte = forms.BooleanField(label="Est représentée par une carte adhérent.", required=False)

    class Meta:
        model = TypeCotisation
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'types_cotisations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Type
        if self.instance and Cotisation.objects.filter(type_cotisation=self.instance):
            self.fields["type"].disabled = True

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme type d'adhésion par défaut"
        if len(TypeCotisation.objects.all()) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            self.fields['defaut'].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_cotisations_liste' %}"),
            Fieldset('Généralités',
                Field('nom'),
                Field('type'),
                Field('carte'),
                Field('defaut'),
            ),
            Fieldset('Options',
                Field('activite'),
                Field('code_comptable'),
                Field('code_analytique'),
                Field("code_produit_local"),
            ),
            Fieldset('Structure associée',
                Field('structure'),
            ),
        )

