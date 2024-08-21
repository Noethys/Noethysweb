# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, ButtonHolder
from crispy_forms.bootstrap import Field
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    donnees = forms.ChoiceField(label="Que souhaitez-vous supprimer ?", initial="occurence", required=False, choices=[
        ("OCCURENCE", "Uniquement l'occurence sélectionnée"), ("TOUTES", "Toutes les occurences de la série"), ("PERIODE", "Les occurences d'une période")])
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget())

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres_supprimer_occurences'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Field("donnees"),
            Field("periode"),
            ButtonHolder(
                HTML("""<button class='btn btn-warning' onclick="$('#form_parametres_supprimer_occurences').submit()"><i class="fa fa-trash margin-r-5"></i>Supprimer</button> """),
                HTML("""<a class="btn btn-danger" href="{{ view.get_success_url }}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""),
                css_class="pull-right",
            ),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
    <script>
        function On_change_donnees() {
            $('#div_id_periode').hide();
            if ($("#id_donnees").val() == 'PERIODE') {
                $('#div_id_periode').show();
            }
        }
        $(document).ready(function() {
            $('#id_donnees').on('change', On_change_donnees);
            On_change_donnees.call($('#id_donnees').get(0));
        });
    
    </script>
"""
