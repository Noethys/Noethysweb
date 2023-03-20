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
from core.utils.utils_commandes import Commandes
from core.models import ComptaCategorie
from core.widgets import Select_avec_commandes_advanced


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = ComptaCategorie
        fields = "__all__"
        widgets = {
            "compte_comptable": Select_avec_commandes_advanced(attrs={"id_form": "comptes_comptables_form", "module_form": "parametrage.forms.comptes_comptables", "nom_objet": "un compte comptable", "champ_nom": "nom"}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "categories_comptables_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'categories_comptables_liste' %}"),
            Fieldset("Généralités",
                Field("type"),
                Field("nom"),
                Field("abrege"),
                Field("compte_comptable"),
            ),
            Fieldset('Structure associée',
                Field('structure'),
            ),
        )
