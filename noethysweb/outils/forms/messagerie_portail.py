# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML
from crispy_forms.bootstrap import Field, StrictButton
from core.models import PortailMessage
from core.forms.base import FormulaireBase
from portail.utils.utils_summernote import SummernoteTextFormField
from core.utils.utils_commandes import Commandes


class Formulaire(FormulaireBase, ModelForm):
    texte = SummernoteTextFormField(label="Poster un message", attrs={'summernote': {'width': '100%', 'height': '200px', 'toolbar': [
        ['font', ['bold', 'underline', 'clear']],
        ['color', ['color']],
        ['para', ['ul', 'ol', 'paragraph']],
        ['insert', ['link', 'picture']],
        ['view', ['codeview', 'help']],
        ]}})

    class Meta:
        model = PortailMessage
        fields = ("famille", "structure", "utilisateur", "texte")

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille", None)
        idstructure = kwargs.pop("idstructure", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_messages_form'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=idfamille),
            Hidden('structure', value=idstructure),
            Hidden('utilisateur', value=self.request.user.pk),
            Field('texte'),
            Commandes(enregistrer_label="<i class='fa fa-send margin-r-5'></i>Envoyer", annuler_url="{% url 'portail_contact' %}", ajouter=False, aide=False, css_class="pull-right"),
        )
