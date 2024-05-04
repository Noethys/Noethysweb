# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.utils.utils_commandes import Commandes
from core.widgets import SelectionActivitesWidget, DateRangePickerWidget
from core.forms.base import FormulaireBase
from core.models import Famille


class Formulaire(FormulaireBase, forms.Form):
    activites = forms.CharField(label="Activités", required=True, widget=SelectionActivitesWidget(attrs={"afficher_colonne_detail": True}))
    periode = forms.CharField(label="Période", required=True, widget=DateRangePickerWidget(attrs={"afficher_check": False}))
    filtre_villes = forms.TypedChoiceField(label="Filtre sur les villes", choices=[(None, "Toutes les villes"), ("SELECTION", "Uniquement les villes sélectionnées")], initial="TOUTES", required=False)
    villes = forms.MultipleChoiceField(label="Sélection de villes", widget=Select2MultipleWidget(), choices=[], required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Villes
        villes = list({famille.ville_resid.upper(): True for famille in Famille.objects.all() if famille.ville_resid}.keys())
        self.fields["villes"].choices = sorted([(ville, ville) for ville in villes if ville])

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'facturation_toc' %}", enregistrer=False, ajouter=False,
                      commandes_principales=[HTML(
                          """<a type='button' class="btn btn-primary margin-r-5" onclick="generer_pdf()" title="Génération du PDF"><i class='fa fa-file-pdf-o margin-r-5'></i>Générer le PDF</a>"""),
                      ]),
            Fieldset("Sélection des prestations",
                Field("periode"),
                Field("activites"),
                Field("filtre_villes"),
                Field("villes"),
            ),
            HTML(EXTRA_HTML),
        )


EXTRA_HTML = """
<script>

    function On_change_villes() {
        $('#div_id_villes').hide();
        if ($("#id_filtre_villes").val() == 'SELECTION') {
            $('#div_id_villes').show();
        };
    }
    $(document).ready(function() {
        $('#id_filtre_villes').on('change', On_change_villes);
        On_change_villes.call($('#id_filtre_villes').get(0));
    });

</script>
"""
