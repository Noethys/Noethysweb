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
from core.models import Message, Famille
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
        idfamille = kwargs.pop("idfamille")

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_message_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit la famille associée
        if self.instance.idmessage== None:
            famille = Famille.objects.get(pk=idfamille)
        else:
            famille = self.instance.famille

        # Focus
        self.fields['texte'].widget.attrs.update({'autofocus': 'autofocus'})

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_resume' idfamille=famille.idfamille %}"),
            Hidden('famille', value=famille.idfamille),
            Hidden('nom', value="nom de la famille ici"),
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
                Field("afficher_facture"),
                Field("rappel_famille"),
                Field("rappel"),
            ),
        )

