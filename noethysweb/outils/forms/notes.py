# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, HTML
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Note, Famille, Individu
from core.widgets import DatePickerWidget
import datetime


class Formulaire(FormulaireBase, ModelForm):
    date_parution = forms.DateField(label="Date de parution", required=False, widget=DatePickerWidget())

    class Meta:
        model = Note
        fields = "__all__"
        exclude = ["famille", "individu"]
        widgets = {
            'texte': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'notes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Focus
        self.fields['texte'].widget.attrs.update({'autofocus': 'autofocus'})

        # Date de parution
        if not self.instance.pk:
            self.fields['date_parution'].initial = datetime.date.today()

        # Afficher sur accueil
        if not self.instance.pk:
            valeur_afficher_accueil = True
        else:
            valeur_afficher_accueil = self.instance.afficher_accueil

        # Création des champs options
        texte_intro = ""
        options = []
        if self.instance.famille:
            texte_intro = "<p>Note pour la famille : %s</p>" % self.instance.famille
            options += [Field("afficher_accueil"), Field("afficher_liste"), Field("afficher_facture"), Field("rappel_famille")]
        if self.instance.individu:
            texte_intro = "<p>Note pour l'individu : %s</p>" % self.instance.individu
            options += [Field("afficher_accueil"), Field("afficher_liste"), Field("afficher_commande"),]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% if request.GET.next %}{{ request.GET.next }}{% else %}{% url 'notes_liste' %}{% endif %}"),
            HTML("<input type='hidden' name='next' value='{{ request.GET.next }}'>"),
            Hidden('type', value="INSTANTANE"),
            Hidden('afficher_accueil', value=valeur_afficher_accueil),
            HTML("<strong>%s</strong>" % texte_intro),
            Fieldset("Note",
                Field("categorie"),
                Field("texte"),
            ),
            Fieldset("Parution",
                Field("date_parution"),
                Field("priorite"),
            ),
            Fieldset("Options",
                *options,
                Field("rappel"),
            ),
        )
