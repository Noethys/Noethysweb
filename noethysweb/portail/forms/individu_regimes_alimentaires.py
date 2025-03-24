# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from crispy_forms.helper import FormHelper
from core.models import Individu, RegimeAlimentaire
from core.widgets import Select_many_avec_plus
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):
    regimes_alimentaires = forms.ModelMultipleChoiceField(label=_("Régimes alimentaires"),
                            widget=Select_many_avec_plus(attrs={"url_ajax": "portail_ajax_ajouter_regime_alimentaire", "afficher_bouton_ajouter": False, "textes": {"champ": _("Nom du régime alimentaire"), "ajouter": _("Ajouter un nouveau régime alimentaire")}}),
                            queryset=RegimeAlimentaire.objects.all().order_by("nom"), required=False)

    class Meta:
        model = Individu
        fields = ["regimes_alimentaires"]

    def __init__(self, *args, **kwargs):
        self.rattachement = kwargs.pop("rattachement", None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "individu_regimes_alimentaires"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_regimes_alimentaires_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Help texte du champ de saisie des régimes
        help_text_regimes = _("Cliquez sur le champ ci-dessus pour faire apparaître la liste de choix et cliquez sur un ou plusieurs éléments dans la liste") + ". "
        if settings.PORTAIL_AUTORISER_AJOUT_REGIME:
            help_text_regimes += "<a href='#' class='ajouter_element'>" + _("Cliquez ici pour ajouter un régime manquant dans la liste de choix") + ".</a>"

        # Help_texts pour le mode édition
        self.help_texts = {
            "regimes_alimentaires": help_text_regimes,
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": _("Régimes"), "champs": ["regimes_alimentaires"]},
        ]

        # Préparation du layout
        self.Set_layout()
