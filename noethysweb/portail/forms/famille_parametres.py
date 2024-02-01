# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from core.models import Famille
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Famille
        fields = ["email_blocage", "mobile_blocage"]
        labels = {
            "email_blocage": "Nous ne souhaitons pas recevoir d'emails groupés",
            "mobile_blocage": "Nous ne souhaitons pas recevoir de SMS groupés",
        }
        help_texts = {
            "email_blocage": None,
            "mobile_blocage": None,
        }

    def __init__(self, *args, **kwargs):
        self.famille = kwargs.pop('famille', None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "famille_parametres"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_parametres_form'
        self.helper.form_method = 'post'

        self.helper.use_custom_control = False

        # Help_texts pour le mode édition
        self.help_texts = {
            "email_blocage": "Cochez cette case pour ne plus recevoir les communications groupées par Email.",
            "mobile_blocage": "Cochez cette case pour ne plus recevoir les communications groupées par SMS.",
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": "Paramètres", "champs": ["email_blocage", "mobile_blocage"]},
        ]

        # Préparation du layout
        self.Set_layout()
