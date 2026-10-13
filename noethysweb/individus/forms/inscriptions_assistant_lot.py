# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.forms.base import FormulaireBase
from core.models import Activite
from core.widgets import Select_activite


class Formulaire_activite(FormulaireBase, forms.Form):
    """ Sélection de l'activité de destination (étape 1 de l'assistant) """
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire_activite, self).__init__(*args, **kwargs)
        # Seules les activités des structures de l'utilisateur sont proposées
        self.fields["activite"].widget.attrs["request"] = self.request
        self.fields["activite"].widget.attrs["id"] = "ail_activite"
