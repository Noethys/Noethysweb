# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from outils.widgets import Anomalies


class Formulaire(FormulaireBase, forms.Form):
    anomalies = forms.CharField(label="Anomalies", required=False, widget=Anomalies(
        attrs={"texte_si_vide": "Aucune anomalie", "hauteur_libre": True, "coche_tout": False}))

    def __init__(self, *args, **kwargs):
        anomalies = kwargs.pop("anomalies", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'anomalies_form'
        self.helper.form_method = 'post'

        self.fields["anomalies"].widget.attrs.update({"anomalies": anomalies})
        self.fields["anomalies"].label = False

        # Affichage
        self.helper.layout = Layout(
            HTML("""
                <div class="mb-3">
                    <button type="submit" class='btn btn-primary' name="corriger"><i class="fa fa-check margin-r-5"></i>Corriger les anomalies cochées</button> 
                </div>
            """),
            Field("anomalies"),
        )
