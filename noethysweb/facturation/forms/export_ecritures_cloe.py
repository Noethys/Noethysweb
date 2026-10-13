# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget, DatePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(attrs={"afficher_check": False}))
    compte_collectif = forms.CharField(label="Compte collectif", max_length=100, initial="411000", help_text="Compte collectif pour les comptes clients.")
    prefixe_c = forms.BooleanField(label="Insérer le préfixe 'C' devant les alias des tiers", initial=True, required=False)
    choix_comptes = [
        ("toutes", "Toutes les familles"),
        ("utilisees", "Uniquement les familles présentes dans les factures et règlements exportés"),
        ("creees_depuis", "Uniquement les familles créées depuis une date donnée"),
        ("aucune", "Aucune (ne pas générer le fichier des comptes clients)"),
    ]
    comptes_clients = forms.ChoiceField(label="Comptes clients", choices=choix_comptes, initial="toutes", required=True,
                                        help_text="Sélectionnez les familles à inclure dans le fichier des comptes clients (CPT).")
    date_creation_familles = forms.DateField(label="Créées depuis le", required=False, widget=DatePickerWidget(),
                                             help_text="Seules les familles créées à partir de cette date (incluse) seront exportées. Indiquez par exemple le lendemain du dernier import.")

    def clean(self):
        if self.cleaned_data.get("comptes_clients") == "creees_depuis" and not self.cleaned_data.get("date_creation_familles"):
            self.add_error("date_creation_familles", "Vous devez renseigner une date de création")
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'facturation_toc' %}", enregistrer=False, ajouter=False,
                      commandes_principales=[HTML(
                          """<a type='button' class="btn btn-primary margin-r-5" onclick="exporter()" title="Exporter"><i class='fa fa-bolt margin-r-5'></i>Exporter</a>"""),
                      ]),
            Fieldset("Paramètres",
                Field("periode"),
                Field("compte_collectif"),
                Field("prefixe_c"),
            ),
            Fieldset("Comptes clients",
                Field("comptes_clients"),
                Field("date_creation_familles"),
            ),
        )
