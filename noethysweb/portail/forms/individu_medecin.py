# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from core.models import Individu, PortailRenseignement, Medecin
from django_select2.forms import ModelSelect2Widget
from portail.forms.fiche import FormulaireBase


class Widget_medecin(ModelSelect2Widget):
    search_fields = ['nom__icontains', 'prenom__icontains', 'ville_resid__icontains']

    def label_from_instance(widget, instance):
        label = instance.Get_nom()
        if instance.ville_resid:
            label += " (%s)" % instance.ville_resid
        return label


class Formulaire(FormulaireBase, ModelForm):
    medecin = forms.ModelChoiceField(label="Médecin", widget=Widget_medecin(attrs={"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}), queryset=Medecin.objects.all().order_by("nom", "prenom"), required=False)

    class Meta:
        model = Individu
        fields = ["medecin"]

    def __init__(self, *args, **kwargs):
        self.rattachement = kwargs.pop("rattachement", None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "individu_medecin"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_medecin_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # self.helper.use_custom_control = False

        # Help_texts pour le mode édition
        self.help_texts = {
            "medecin": "Sélectionnez un médecin dans la liste déroulante. Vous pouvez faire une recherche par nom, par prénom ou par ville.",
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": "Médecin traitant", "champs": ["medecin"]},
        ]

        # Préparation du layout
        self.Set_layout()
