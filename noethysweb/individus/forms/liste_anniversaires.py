# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    activites = forms.CharField(label="Inscrits aux activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": True}))
    presents = forms.CharField(label="Uniquement les présents", required=False, widget=DateRangePickerWidget(attrs={"afficher_check": True}))
    afficher_photos = forms.ChoiceField(label="Afficher les photos", choices=[("0", "Non"), ("16", "Petite taille"), ("32", "Moyenne taille"), ("64", "Grande taille")], initial="non", required=False)
    theme = forms.ChoiceField(label="Thème graphique", choices=[("feuille", "Feuille d'été"), ("cailloux", "Plage de cailloux"), ("gouttes", "Gouttes d'eau"), ("lignes", "Ballet de lignes"), ("montgolfiere", "Montgolfières"), ("mosaique", "Mosaïque")], initial="feuille", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'individus_toc' %}", enregistrer=False, ajouter=False,
                      commandes_principales=[HTML(
                          """<a type='button' class="btn btn-primary margin-r-5" onclick="generer_pdf()" title="Génération du PDF"><i class='fa fa-file-pdf-o margin-r-5'></i>Générer le PDF</a>"""),
                      ]),
            Fieldset("Sélection des individus",
                Field('activites'),
                Field('presents'),
            ),
            Fieldset("Options",
                Field('afficher_photos'),
                Field('theme'),
            ),
        )
