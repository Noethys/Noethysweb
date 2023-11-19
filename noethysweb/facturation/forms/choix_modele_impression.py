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
from core.models import ModeleImpression


class Formulaire(FormulaireBase, forms.Form):
    modele_impression = forms.ChoiceField(label="Modèle d'impression", widget=Select2Widget(), choices=[], required=True)

    def __init__(self, *args, **kwargs):
        categorie = kwargs.pop("categorie", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'choix_modele_impression_form'
        self.helper.form_method = 'post'

        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-md-4'
        # self.helper.field_class = 'col-md-8'

        # Charge les modèles disponibles
        self.fields["modele_impression"].choices = [(0, "Aucun")] + [(modele.pk, modele.nom) for modele in ModeleImpression.objects.filter(categorie=categorie).order_by("nom")]

        # Charge le modèle par défaut
        modele_defaut = ModeleImpression.objects.filter(categorie=categorie, defaut=True)
        if modele_defaut:
            self.fields["modele_impression"].initial = modele_defaut.first().pk

        # Affichage
        self.helper.layout = Layout(
            Fieldset("Modèle d'impression",
                Field("modele_impression"),
            ),
        )
