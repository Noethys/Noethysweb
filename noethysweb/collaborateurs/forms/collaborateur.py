# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML
from crispy_forms.bootstrap import Field, FormActions
from core.forms.select2 import Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.models import Collaborateur


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Collaborateur
        fields = ["civilite", "nom", "prenom", "groupes"]
        widgets = {
            "groupes": Select2MultipleWidget({"data-minimum-input-length": 0}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'collaborateurs_form'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Field("civilite"),
            Field("nom"),
            Field("prenom"),
            Field("groupes"),
            FormActions(
                Submit('submit', 'Enregistrer', css_class='btn-primary'),
                HTML("""<a class="btn btn-danger" href="{% url 'collaborateur_liste' %}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""))
        )
