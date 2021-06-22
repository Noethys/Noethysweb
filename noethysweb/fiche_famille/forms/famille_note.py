# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Note, Individu
from core.widgets import DatePickerWidget
import datetime


class Formulaire(FormulaireBase, ModelForm):
    date_parution = forms.DateField(label="Date de parution", required=False, widget=DatePickerWidget())

    class Meta:
        model = Note
        fields = "__all__"
        widgets = {
            'texte': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_notes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Focus
        self.fields['texte'].widget.attrs.update({'autofocus': 'autofocus'})

        # Date de parution
        if not self.instance.pk:
            self.fields['date_parution'].initial = datetime.date.today()

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_resume' idfamille=idfamille %}"),
            Hidden('famille', value=idfamille),
            Hidden('type', value="INSTANTANE"),
            Fieldset("Note",
                Field("categorie"),
                Field("texte"),
            ),
            Fieldset("Parution",
                Field("date_parution"),
                Field("priorite"),
            ),
            Fieldset("Options",
                Field("afficher_accueil"),
                Field("afficher_liste"),
                Field("afficher_facture"),
                Field("rappel_famille"),
                Field("rappel"),
            ),
        )
