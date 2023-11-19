# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2Widget
from core.models import LotFactures
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    lot_factures = forms.ModelChoiceField(label="Lot de factures", widget=Select2Widget(), queryset=LotFactures.objects.all().order_by("-pk"), required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_parametres'
        self.helper.form_method = 'post'

        self.helper.layout = Layout(
            Field("lot_factures"),
        )
