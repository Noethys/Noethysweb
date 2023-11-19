# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2Widget
from core.models import ModeleWord
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    modele = forms.ModelChoiceField(label="Modèle de document", widget=Select2Widget(), queryset=ModeleWord.objects.filter(categorie="contrat_collaborateur").order_by("nom"), required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'choix_modele_form'
        self.helper.form_method = 'post'

        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-md-4'
        # self.helper.field_class = 'col-md-8'

        # Charge le modèle de document par défaut
        modele_defaut = ModeleWord.objects.filter(categorie="contrat_collaborateur", defaut=True)
        if modele_defaut:
            self.fields["modele"].initial = modele_defaut.first()

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Modèle de document Word",
                Field("modele"),
            ),
        )
