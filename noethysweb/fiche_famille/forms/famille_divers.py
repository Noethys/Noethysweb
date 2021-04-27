# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Famille, Rattachement


class Formulaire(ModelForm):
    mail = forms.ChoiceField(label="Mail favori", choices=[], required=False)

    class Meta:
        model = Famille
        fields = ["mail", "code_compta", "titulaire_helios", "idtiers_helios", "natidtiers_helios", "reftiers_helios", "cattiers_helios", "natjur_helios"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_divers_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        rattachements = Rattachement.objects.select_related("individu").filter(famille_id=idfamille, titulaire=True).order_by("individu__nom", "individu__prenom")

        # Mail favori
        self.fields["mail"].choices = [(None, "---------")] + [(rattachement.individu.mail, rattachement.individu.mail) for rattachement in rattachements if rattachement.individu.mail]

        # Titulaire hélios
        self.fields["titulaire_helios"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_resume' idfamille=idfamille %}", ajouter=False),
            Fieldset("Email",
                Field("mail"),
            ),
            Fieldset("Comptabilité",
                Field("code_compta"),
            ),
            Fieldset("Données tiers pour Hélios",
                Field("titulaire_helios"),
                Field("idtiers_helios"),
                Field("natidtiers_helios"),
                Field("reftiers_helios"),
                Field("cattiers_helios"),
                Field("natjur_helios"),
            ),
        )

    def clean(self):
        return self.cleaned_data

