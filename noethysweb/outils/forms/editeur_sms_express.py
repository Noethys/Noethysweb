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
from core.models import SMS, ConfigurationSMS, Rattachement
from core.utils.utils_commandes import Commandes
from outils.forms.editeur_sms import EXTRA_HTML
from outils.widgets import Texte_SMS


class Formulaire(FormulaireBase, ModelForm):
    objet = forms.CharField(label="Objet", required=False)
    destinataire = forms.ChoiceField(label="Destinataire", choices=[], required=True)

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
        self.helper.attrs = {'enctype': 'multipart/form-data'}

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Sélectionne l'adresse d'expédition
        self.fields["configuration_sms"].queryset = ConfigurationSMS.objects.filter(pk__in=self.request.user.Get_configurations_sms_possibles())
        if not self.fields["configuration_sms"].queryset.count():
            self.fields['configuration_sms'].help_text = """<span class='text-danger'><i class='fa fa-warning text-danger'></i> Vous devez vérifier qu'une configuration SMS a été créée dans le menu 
                                                    Paramétrage > Configurations SMS et que vous l'avez rattachée à la structure (Menu Paramétrage > Structures). Vous pouvez
                                                    également associer une configuration SMS à votre compte utilisateur dans la partie Administrateur.</span>"""
        if not idsms:
            self.fields['configuration_sms'].initial = self.request.user.Get_configuration_sms_defaut()

        # Définit la taille max du texte
        configuration_sms = self.instance.configuration_sms if self.instance.pk else self.fields['configuration_sms'].initial
        if configuration_sms:
            self.fields['texte'].widget.attrs['maxlength'] = configuration_sms.nbre_caracteres

        # Destinataire
        if self.instance:
            destinataire = self.instance.destinataires.first()

            if destinataire.famille:
                rattachements = Rattachement.objects.select_related("individu").filter(famille=destinataire.famille, titulaire=True).order_by("individu__nom", "individu__prenom")
                self.fields["destinataire"].choices = [(None, "---------")] + [(rattachement.individu.tel_mobile, "%s (%s)" % (rattachement.individu.tel_mobile, rattachement.individu.Get_nom())) for rattachement in rattachements if rattachement.individu.tel_mobile]
                self.fields["destinataire"].initial = destinataire.famille.mobile

            if destinataire.collaborateur:
                self.fields["destinataire"].choices = [(None, "---------")]
                if destinataire.collaborateur.tel_mobile:
                    self.fields["destinataire"].choices.append((destinataire.collaborateur.tel_mobile, "%s (%s)" % (destinataire.collaborateur.tel_mobile, destinataire.collaborateur.Get_nom())))
                    self.fields["destinataire"].initial = destinataire.collaborateur.tel_mobile

        # Affichage
        self.helper.layout = Layout(
            Hidden("idsms", value=self.instance.pk),
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False,
                      autres_commandes=[
                          HTML("""<a class="btn btn-primary" id="bouton_envoyer_sms" title="Envoyer"><i class="fa fa-send-o margin-r-5"></i>Envoyer</a> """),
                          HTML("""<a class="btn btn-danger" title="Fermer" onclick="$('#modal_editeur_sms').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Fermer</a> """),
                          HTML("""<button type="submit" name="enregistrer_brouillon" title="Enregistrer le brouillon" class="btn btn-default"><i class="fa fa-save margin-r-5"></i>Enregistrer le brouillon</button> """),
                          HTML(EXTRA_HTML),
                      ],
            ),
            Field('objet'),
            Field('configuration_sms'),
            Field('destinataire'),
            Field('texte'),
        )
