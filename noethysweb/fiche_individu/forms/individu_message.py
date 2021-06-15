# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Message, Individu
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    date_parution = forms.DateField(label="Date de parution", required=False, widget=DatePickerWidget())

    class Meta:
        model = Message
        fields = "__all__"
        widgets = {
            'texte': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu")

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_message_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if self.instance.idmessage== None:
            individu = Individu.objects.get(pk=idindividu)
        else:
            individu = self.instance.individu

        # Focus
        self.fields['texte'].widget.attrs.update({'autofocus': 'autofocus'})

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'individu_resume' idfamille=idfamille idindividu=idindividu %}"),
            Hidden('individu', value=individu.idindividu),
            Hidden('nom', value=individu),
            Hidden('type', value="INSTANTANE"),
            Fieldset("Message",
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
                Field("afficher_commande"),
                Field("rappel"),
            ),
        )

