# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden
from crispy_forms.bootstrap import Field
from django_summernote.utils import get_theme_files, get_config, has_codemirror_config
from django_summernote.widgets import SummernoteInplaceWidget
from core.models import PortailMessage
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from portail.utils.utils_summernote import SummernoteTextFormField


class SummernoteInplaceWidgetBS5(SummernoteInplaceWidget):
    """ Force les assets Summernote en thème Bootstrap 5, indépendamment de SUMMERNOTE_THEME (global = bs4). """
    def _media(self):
        config = get_config()
        return forms.Media(
            css={'all': (config['codemirror_css'] if has_codemirror_config() else ())
                        + get_theme_files('bs5', 'default_css')
                        + config['css_for_inplace']},
            js=(config['codemirror_js'] if has_codemirror_config() else ())
                + get_theme_files('bs5', 'default_js')
                + config['js_for_inplace'],
        )
    media = property(_media)


class Formulaire(FormulaireBase, ModelForm):
    texte = SummernoteTextFormField(label=_("Poster un message"), attrs={'summernote': {'width': '100%', 'height': '200px', 'toolbar': [
        ['font', ['bold', 'underline', 'clear']],
        # ['color', ['color']],
        # ['para', ['ul', 'ol', 'paragraph']],
        ['insert', ['link', 'picture']],
        ['view', ['codeview', 'help']],
        ]}})

    class Meta:
        model = PortailMessage
        fields = ("famille", "structure", "texte")

    def __init__(self, *args, **kwargs):
        idstructure = kwargs.pop("idstructure", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_messages_form'
        self.helper.form_method = 'post'

        self.fields["texte"].widget = SummernoteInplaceWidgetBS5(attrs=self.fields["texte"].widget.attrs)

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=self.request.user.famille.pk),
            Hidden('structure', value=idstructure),
            Field('texte'),
            Commandes(enregistrer_label="<i class='fa fa-send margin-r-5'></i>%s" % _("Envoyer"), annuler_url="{% url 'portail_contact' %}", ajouter=False, aide=False, css_class="pull-right"),
        )
