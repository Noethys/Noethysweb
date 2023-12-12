# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.models import Information
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Information
        fields = ["individu", "categorie", "intitule", "description", "document"]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            "categorie": _("Sélectionnez une catégorie dans la liste proposée."),
            "intitule": _("Saisissez l'intitulé de l'information. Exemple : Allergie aux oeufs."),
            "description": _("Précisez si besoin une description détaillée."),
            "document": _("Vous pouvez ajouter un document si besoin (PDF ou image)."),
        }

    def __init__(self, *args, **kwargs):
        rattachement = kwargs.pop("rattachement", None)
        mode = kwargs.pop("mode", "MODIFICATION")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_informations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # self.helper.use_custom_control = False

        # Affichage
        self.helper.layout = Layout(
            Hidden('individu', value=rattachement.individu_id),
            Fieldset(_("Information"),
                Field("categorie"),
                Field("intitule"),
                Field("description"),
                Field("document"),
            ),
            Commandes(annuler_url="{% url 'portail_individu_informations' idrattachement=rattachement.pk %}", aide=False, ajouter=False, css_class="pull-right"),
        )
