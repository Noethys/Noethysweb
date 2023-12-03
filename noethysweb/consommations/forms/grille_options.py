# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    tri = forms.ChoiceField(label="Tri des individus", choices=[("nom", "Nom"), ("prenom", "Prénom"), ("date_naiss", "date de naissance")], initial="nom", required=False)
    afficher_age = forms.ChoiceField(label="Afficher l'âge", choices=[("oui", "Oui"), ("non", "Non")], initial="non", required=False)
    afficher_date_naiss = forms.ChoiceField(label="Afficher la date de naissance", choices=[("oui", "Oui"), ("non", "Non")], initial="non", required=False)
    afficher_groupe = forms.ChoiceField(label="Afficher le groupe", choices=[("oui", "Oui"), ("non", "Non")], initial="non", required=False)
    afficher_classe = forms.ChoiceField(label="Afficher la classe", choices=[("oui", "Oui"), ("non", "Non")], initial="non", required=False)
    afficher_niveau_scolaire = forms.ChoiceField(label="Afficher le niveau scolaire", choices=[("oui", "Oui"), ("non", "Non")], initial="non", required=False)
    afficher_presents_totaux = forms.ChoiceField(label="Afficher présents dans totaux", choices=[("oui", "Oui"), ("non", "Non")], initial="non", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_options'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-5'
        self.helper.field_class = 'col-md-7'

        self.helper.layout = Layout(
            Field("tri"),
            Field("afficher_age"),
            Field("afficher_date_naiss"),
            Field("afficher_groupe"),
            Field("afficher_classe"),
            Field("afficher_niveau_scolaire"),
            Field("afficher_presents_totaux"),
        )
