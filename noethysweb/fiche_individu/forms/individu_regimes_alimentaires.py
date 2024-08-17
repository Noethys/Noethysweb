# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Individu, RegimeAlimentaire
from core.widgets import Select_many_avec_plus


class Formulaire(FormulaireBase, ModelForm):
    regimes_alimentaires = forms.ModelMultipleChoiceField(label=_("Régimes alimentaires"),
                            widget=Select_many_avec_plus(attrs={"url_ajax": "ajax_ajouter_regime_alimentaire", "textes": {"champ": _("Nom du régime alimentaire"), "ajouter": _("Ajouter un nouveau régime alimentaire")}}),
                            queryset=RegimeAlimentaire.objects.all().order_by("nom"), required=False, help_text=_("Cliquez sur le champ ci-dessus pour faire apparaître la liste de choix ou tapez les premières lettres du régime recherché. Cliquez sur le '+' pour ajouter un régime manquant dans la liste de choix."))

    class Meta:
        model = Individu
        fields = ["regimes_alimentaires"]

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_regimes_alimentaires_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="individu_regimes_alimentaires_modifier", modifier_args="idfamille=idfamille idindividu=idindividu",
                                  modifier=self.request.user.has_perm("core.individu_regimes_alimentaires_modifier"), enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        elif self.mode == "EDITION":
            commandes = Commandes(annuler_url="{% url 'individu_regimes_alimentaires' idfamille=idfamille idindividu=idindividu %}", ajouter=False)
        else:
            commandes = Commandes(annuler_url="{% url 'regimes_alimentaires_liste' %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Field("regimes_alimentaires"),
        )
