# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.models import LigneModelePlanningCollaborateur, TypeEvenementCollaborateur


class Formulaire(forms.ModelForm):
    idligne = forms.CharField(widget=forms.HiddenInput(), required=False)
    index = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = LigneModelePlanningCollaborateur
        exclude = ["modele",]
        widgets = {
            "heure_debut": forms.TimeInput(attrs={'type': 'time'}),
            "heure_fin": forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "ligne_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Type d'évènement
        types_evenements = TypeEvenementCollaborateur.objects.all().order_by("nom")
        self.fields["type_evenement"].choices = [(None, "---------")] + [(type_evenement.pk, type_evenement.nom) for type_evenement in types_evenements]
        self.fields["type_evenement"].required = True

        self.helper.layout = Layout(
            Field("idligne"),
            Field("index"),
            Field("jour"),
            Field("periode"),
            Field("heure_debut"),
            Field("heure_fin"),
            Field("type_evenement"),
            Field("titre"),
        )
