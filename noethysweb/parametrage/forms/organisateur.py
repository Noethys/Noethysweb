# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, HTML, Row, Div, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions
from core.utils.utils_commandes import Commandes
from core.models import Organisateur
from core.widgets import Telephone, CodePostal, Ville, Selection_image



class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Organisateur
        fields = ['nom', 'rue', 'cp', 'ville', 'tel', 'fax', 'mail', 'site',
                  'num_agrement', 'num_siret', 'code_ape', 'logo']
        widgets = {
            'tel': Telephone(),
            'fax': Telephone(),
            'rue': forms.Textarea(attrs={'rows': 2}),
            'cp': CodePostal(attrs={"id_ville": "id_ville"}),
            'ville': Ville(attrs={"id_codepostal": "id_cp"}),
            'logo': Selection_image(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'organisateur_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'parametrage_toc' %}", ajouter=False),
            Fieldset("Généralités",
                Field('nom'),
            ),
            Fieldset("Coordonnées",
                Field('rue'),
                Field('cp'),
                Field('ville'),
                Field('tel'),
                Field('fax'),
                Field('mail'),
                Field('site'),
            ),
            Fieldset("Numéros d'identification",
                Field('num_agrement'),
                Field('num_siret'),
                Field('code_ape'),
            ),
            Fieldset("Logo",
                Div(
                    Field('logo'),
                ),
            ),
            HTML("<br>"),
        )

