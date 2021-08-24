# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Individu, TypeMaladie
from django_select2.forms import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    maladies = forms.ModelMultipleChoiceField(label="Maladies", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), queryset=TypeMaladie.objects.all().order_by("nom"), required=False)

    class Meta:
        model = Individu
        fields = ["maladies"]

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_maladies_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="individu_maladies_modifier", modifier_args="idfamille=idfamille idindividu=idindividu", modifier=True, enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        elif self.mode == "EDITION":
            commandes = Commandes(annuler_url="{% url 'individu_maladies' idfamille=idfamille idindividu=idindividu %}", ajouter=False)
        else:
            commandes = Commandes(annuler_url="{% url 'maladies_liste' %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Field("maladies"),
        )
