# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, ButtonHolder, Fieldset, Div, Button
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.widgets import Selection_image


class Formulaire(forms.Form):
    photo = forms.ImageField(label="Photo", required=True, widget=Selection_image(attrs={"masquer_image": True}))
    data = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_importation_photos'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.form_show_labels = False
        self.helper.use_custom_control = False

        # Affichage
        self.helper.layout = Layout(
            Field('photo'),
            Field('data'),
            ButtonHolder(
                Div(
                    Submit('bouton_submit', _("Analyser l'image"), css_class='btn-primary'),
                    HTML("""<a class="btn btn-danger" href="{% url 'individus_toc' %}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""),
                    css_class="text-right"
                ),
            ),
        )
