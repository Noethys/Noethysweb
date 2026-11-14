# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import TypeCongeCollaborateur


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = TypeCongeCollaborateur
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "nom": "Exemples : Congés annuels, RTT, Récupération, Compte épargne-temps...",
            "abrege": "Abréviation affichée dans les tableaux (exemples : CA, RTT, RÉC).",
            "ordre": "Ordre d'affichage des compteurs.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "types_conges_collaborateurs_form"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_conges_collaborateurs_liste' %}"),
            Fieldset("Généralités",
                Field("nom"),
                Field("abrege"),
                Field("actif"),
                Field("ordre"),
                Field("observations"),
            ),
            Fieldset("Compteur",
                Field("categorie"),
                Field("unite"),
                Field("mois_debut"),
                Field("solde_negatif"),
            ),
        )
