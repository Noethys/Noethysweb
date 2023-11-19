# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2Widget
from core.models import LotFactures
from core.utils.utils_commandes import Commandes
from core.widgets import DateRangePickerWidget
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    choix_type_selection = [("LOT", "Selon le lot de factures"), ("DATE_EDITION", "Selon la date d'édition")]
    type_selection = forms.TypedChoiceField(label="Type de sélection", choices=choix_type_selection, initial="LOT", required=False)
    lot = forms.ModelChoiceField(label="Lot de factures", widget=Select2Widget({"data-minimum-input-length": 0}),
                                           queryset=LotFactures.objects.all().order_by("-pk"), required=False)
    date_edition = forms.CharField(label="Date d'édition", widget=DateRangePickerWidget(attrs={"afficher_check": False}), required=False)

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
                          """<a type='button' class="btn btn-primary margin-r-5" onclick="generer_pdf()" title="Génération du PDF"><i class='fa fa-file-pdf-o margin-r-5'></i>Générer le PDF</a>"""),
                      ]),
            Fieldset("Sélection des factures",
                Field("type_selection"),
                Field("lot"),
                Field("date_edition"),
                HTML(EXTRA_HTML),
            ),
        )

EXTRA_HTML = """
<script>
    function On_change_type_selection() {
        $('#div_id_lot').hide();
        $('#div_id_date_edition').hide();
        if ($("#id_type_selection").val() == "LOT") {
            $('#div_id_lot').show();
        };
        if ($("#id_type_selection").val() == "DATE_EDITION") {
            $('#div_id_date_edition').show();
        };
    }
    $(document).ready(function() {
        $('#id_type_selection').on('change', On_change_type_selection);
        On_change_type_selection.call($('#id_type_selection').get(0));
    });
</script>
"""
