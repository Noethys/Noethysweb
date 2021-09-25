# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, InlineRadios
from core.widgets import DatePickerWidget
from core.utils.utils_commandes import Commandes
from core.models import Assurance


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Assurance
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        self.idindividu = kwargs.pop("idindividu")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_assurances_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Date de début
        self.fields["date_debut"].initial = datetime.date.today()

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=self.idfamille),
            Hidden('individu', value=self.idindividu),
            Commandes(annuler_url="{% url 'individu_assurances_liste' idfamille=idfamille idindividu=idindividu %}"),
            Fieldset("Généralités",
                Field("assureur"),
                Field("num_contrat"),
            ),
            Fieldset("Période de validité",
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset("Document numérisé",
                Field('document'),
            ),
        )
