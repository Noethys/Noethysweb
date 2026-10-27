# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import NoteCategorie


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = NoteCategorie
        fields = "__all__"
        help_texts = {
            "nom": "Saisissez le nom de la catégorie de notes. Exemples : Comptabilité, Santé, Transport...",
            "priorite": "Sélectionnez la priorité habituelle des notes de cette catégorie.",
            "afficher_accueil": "Cochez cette case si les notes de cette catégorie ont vocation à être affichées sur la page d'accueil.",
            "afficher_liste": "Cochez cette case si les notes de cette catégorie ont vocation à être affichées sur la liste des consommations.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'notes_categories_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'notes_categories_liste' %}"),
            Field('nom'),
            Field('priorite'),
            Field('afficher_accueil'),
            Field('afficher_liste'),
        )

