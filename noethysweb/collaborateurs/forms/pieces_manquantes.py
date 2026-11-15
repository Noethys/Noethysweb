# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.forms.select2 import Select2MultipleWidget
from core.models import GroupeCollaborateurs
from core.widgets import DatePickerWidget

CHOIX_ETATS = [
    ("ABSENTE", "Non fournies"),
    ("EXPIREE", "Expirées"),
    ("BIENTOT", "Expirant bientôt"),
    ("REFUSEE", "Refusées"),
    ("ATTENTE", "Transmises, à vérifier"),
]


class Formulaire(FormulaireBase, forms.Form):
    date = forms.DateField(label="Date de référence", required=True, widget=DatePickerWidget(),
                           help_text="Une pièce est valable si sa date de fin est postérieure ou égale à cette date.")
    delai_expiration = forms.IntegerField(label="Alerte avant expiration (jours)", required=False, initial=30, min_value=0, max_value=365,
                                          help_text="Signale les pièces valables qui expirent dans ce délai. Saisissez 0 pour ne pas les signaler.")
    situation = forms.ChoiceField(label="Collaborateurs", required=True, initial="en_poste",
                                  choices=[("en_poste", "En poste à la date de référence"), ("a_venir", "En poste ou dont le contrat est à venir"), ("tous", "Tous les collaborateurs")])
    groupes = forms.ModelMultipleChoiceField(label="Groupes de collaborateurs", queryset=GroupeCollaborateurs.objects.all().order_by("nom"), required=False,
                                             widget=Select2MultipleWidget({"data-minimum-input-length": 0}), help_text="Laissez vide pour tous les collaborateurs.")
    etats = forms.MultipleChoiceField(label="Pièces à afficher", choices=CHOIX_ETATS, required=True, widget=forms.CheckboxSelectMultiple,
                                      initial=["ABSENTE", "EXPIREE", "BIENTOT", "REFUSEE", "ATTENTE"])

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = "post"
        self.fields["date"].initial = datetime.date.today()

        self.helper.layout = Layout(
            Field("date"),
            Field("delai_expiration"),
            Field("situation"),
            Field("groupes"),
            Field("etats"),
        )
