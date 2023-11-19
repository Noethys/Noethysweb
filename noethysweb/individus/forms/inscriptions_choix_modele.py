# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.forms.base import FormulaireBase
from core.forms.select2 import Select2Widget
from core.models import ModeleDocument

class Formulaire(FormulaireBase, forms.Form):
    modele = forms.ModelChoiceField(label="Modèle de document", widget=Select2Widget(), queryset=ModeleDocument.objects.filter(categorie="inscription").order_by("nom"), required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'choix_modele_form'
        self.helper.form_method = 'post'

        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-md-3'
        # self.helper.field_class = 'col-md-9'

        # Charge le modèle de document par défaut
        modele_defaut = ModeleDocument.objects.filter(categorie="inscription", defaut=True)
        if modele_defaut:
            self.fields["modele"].initial = modele_defaut.first()

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Modèle de document",
                Field("modele"),
            ),
        )

