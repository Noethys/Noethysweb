# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase
from facturation.utils.utils_export_sage import PRESETS_SAGE


class Formulaire(FormulaireBase, forms.Form):
    version_sage = forms.ChoiceField(label="Version de Sage", choices=[(code, preset["libelle"]) for code, preset in PRESETS_SAGE.items()], initial="sage100",
                                     help_text="Détermine les conventions par défaut (compte clients, séparateur, gestion de l'analytique). Tous les paramètres restent personnalisables ci-dessous.")
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(attrs={"afficher_check": False}))
    compte_clients = forms.CharField(label="Compte clients", max_length=100, initial="41100000",
                                     help_text="Compte général collectif utilisé pour les contreparties clients (ex : 41100000 pour Sage 100, 411000 pour Sage 50).")
    code_journal_ventes = forms.CharField(label="Code journal ventes", max_length=100, initial="VT", required=False,
                                          help_text="Code journal utilisé pour les écritures de factures.")
    code_journal_reglements = forms.CharField(label="Code journal règlements", max_length=100, initial="BQ", required=False,
                                              help_text="Code par défaut utilisé uniquement si aucun code n'est trouvé dans le paramétrage du mode de règlement.")
    plan_analytique = forms.CharField(label="Plan analytique", max_length=100, initial="", required=False,
                                      help_text="Numéro ou code du plan analytique Sage. Utilisé uniquement pour le format Sage 100 avec analytique par doublement des lignes.")
    format_date = forms.ChoiceField(label="Format des dates", choices=[("jjmmaaaa", "JJ/MM/AAAA"), ("aaaammjj", "AAAAMMJJ")], initial="jjmmaaaa")
    separateur = forms.ChoiceField(label="Séparateur de colonnes", choices=[("point_virgule", "Point-virgule ( ; )"), ("tabulation", "Tabulation"), ("virgule", "Virgule ( , )"), ("barre", "Barre verticale ( | )")], initial="tabulation")
    separateur_decimal = forms.ChoiceField(label="Séparateur décimal", choices=[("virgule", "Virgule ( , )"), ("point", "Point ( . )")], initial="virgule",
                                           help_text="Sage attend généralement la virgule. Le point est forcé automatiquement si le séparateur de colonnes est la virgule.")
    entete = forms.BooleanField(label="Inclure la ligne d'en-tête", initial=True, required=False,
                                help_text="Décochez si votre format d'import paramétrable Sage ne doit pas comporter de ligne de titres.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'facturation_toc' %}", enregistrer=False, ajouter=False,
                      commandes_principales=[HTML(
                          """<a type='button' class="btn btn-primary margin-r-5" onclick="exporter()" title="Exporter"><i class='fa fa-bolt margin-r-5'></i>Exporter</a>"""),
                      ]),
            Fieldset("Paramètres",
                Field("version_sage"),
                Field("periode"),
                Field("compte_clients"),
                Field("code_journal_ventes"),
                Field("code_journal_reglements"),
                Field("plan_analytique"),
            ),
            Fieldset("Format du fichier",
                Field("format_date"),
                Field("separateur"),
                Field("separateur_decimal"),
                Field("entete"),
            ),
        )
