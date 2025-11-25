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


class Formulaire(FormulaireBase, forms.Form):
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(attrs={"afficher_check": False}))
    code_journal_ventes = forms.CharField(label="Code journal ventes", max_length=100, initial="VE", required=False, help_text="Code par défaut qui sera utilisé uniquement si aucune code n'est trouvé dans le paramétrage.")
    code_journal_reglements = forms.CharField(label="Code journal règlements", max_length=100, initial="", required=False, help_text="Code par défaut qui sera utilisé uniquement si aucune code n'est trouvé dans le paramétrage.")
    ligne_vide = forms.BooleanField(label="Séparer les écritures avec une ligne vide", initial=True, required=False)

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
                Field("code_journal_ventes"),
                Field("code_journal_reglements"),
                Field("ligne_vide"),
            ),
        )
