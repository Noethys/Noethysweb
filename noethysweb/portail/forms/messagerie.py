# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from re import UNICODE, compile
from django.forms import ModelForm
from django.utils.translation import gettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden
from crispy_forms.bootstrap import Field
from core.models import PortailMessage
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from portail.utils.utils_summernote import SummernoteTextFormField


class Formulaire(FormulaireBase, ModelForm):
    texte = SummernoteTextFormField(label=_("Poster un message"), attrs={'summernote': {'width': '100%', 'height': '200px', 'toolbar': [
        ['font', ['bold', 'underline', 'clear']],
        ['color', ['color']],
        ['para', ['ul', 'ol', 'paragraph']],
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

        # Affichage
        self.helper.layout = Layout(
            Hidden('famille', value=self.request.user.famille.pk),
            Hidden('structure', value=idstructure),
            Field('texte'),
            Commandes(enregistrer_label="<i class='fa fa-send margin-r-5'></i>%s" % _("Envoyer"), annuler_url="{% url 'portail_contact' %}", ajouter=False, aide=False, css_class="pull-right"),
        )

    # def clean_texte(self):
    #     # Retrait des emojis qui causent une erreur de charset MySQL
    #     emoji_pattern = compile("["
    #                             u"\U0001F600-\U0001F64F"  # emoticons
    #                             u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    #                             u"\U0001F680-\U0001F6FF"  # transport & map symbols
    #                             u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
    #                             u"\U0001F1F2-\U0001F1F4"  # Macau flag
    #                             u"\U0001F1E6-\U0001F1FF"  # flags
    #                             u"\U0001F600-\U0001F64F"
    #                             u"\U00002702-\U000027B0"
    #                             u"\U000024C2-\U0001F251"
    #                             u"\U0001f926-\U0001f937"
    #                             u"\U0001F1F2"
    #                             u"\U0001F1F4"
    #                             u"\U0001F620"
    #                             u"\u200d"
    #                             u"\u2640-\u2642"
    #                             "]+", flags=UNICODE)
    #     texte = emoji_pattern.sub(r'', self.cleaned_data["texte"])
    #     return texte
