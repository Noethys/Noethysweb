# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import SMS, ConfigurationSMS
from outils.widgets import Texte_SMS


class Formulaire(FormulaireBase, ModelForm):
    action = forms.CharField(label="Action", required=False)

    class Meta:
        model = SMS
        fields = "__all__"
        widgets = {
            "texte": Texte_SMS(),
        }
        help_texts = {
            "objet": "Saisissez un titre qui vous permettra de retrouver plus facilement ce SMS dans l'historique. Ce titre n'apparaît pas dans le SMS."
        }

    def __init__(self, *args, **kwargs):
        idsms = kwargs.pop("idsms", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_editeur_sms'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Sélectionne l'adresse d'expédition
        self.fields["configuration_sms"].queryset = ConfigurationSMS.objects.filter(pk__in=self.request.user.Get_configurations_sms_possibles())
        if not idsms:
            self.fields['configuration_sms'].initial = self.request.user.Get_configuration_sms_defaut()

        # Définit la taille max du texte
        configuration_sms = self.instance.configuration_sms if self.instance.pk else self.fields['configuration_sms'].initial
        if configuration_sms:
            self.fields['texte'].widget.attrs['maxlength'] = configuration_sms.nbre_caracteres

        self.fields['selection'].required = False

        # Affichage
        self.helper.layout = Layout(
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False, autres_commandes=[
                    HTML("""<a class="btn btn-primary" id="bouton_envoyer" title="Envoyer"><i class="fa fa-send-o margin-r-5"></i>Envoyer</a> """),
                    HTML("""<a class="btn btn-danger" title="Fermer" href='{% url 'outils_toc' %}'><i class="fa fa-ban margin-r-5"></i>Fermer</a> """),
                    HTML("""<button type="submit" name="enregistrer_brouillon" title="Enregistrer le brouillon" class="btn btn-default"><i class="fa fa-save margin-r-5"></i>Enregistrer le brouillon</button> """),
                ],
            ),
            Hidden('action', value=''),
            Field('objet'),
            Field('configuration_sms'),
            Field('texte'),
            Field("selection"),
        )
