# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from core.utils.utils_commandes import Commandes
from crispy_forms.bootstrap import Field, StrictButton
from core.models import Famille, Rattachement


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Famille
        fields = ["caisse", "num_allocataire", "allocataire", "autorisation_cafpro"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_caisse_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit la famille associée
        famille = Famille.objects.get(pk=idfamille)

        # Allocataire
        rattachements = Rattachement.objects.select_related('individu').filter(famille=famille).order_by("individu__nom", "individu__prenom")
        self.fields["allocataire"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="famille_caisse_modifier", modifier_args="idfamille=idfamille",
                                  modifier=self.request.user.has_perm("core.famille_caisse_modifier"), enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'famille_caisse' idfamille=idfamille %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Field("caisse"),
            Field("num_allocataire"),
            Field("allocataire"),
            Field("autorisation_cafpro"),
        )

    def clean(self):
        return self.cleaned_data

