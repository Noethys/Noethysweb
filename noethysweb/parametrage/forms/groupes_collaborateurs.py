# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django_select2.forms import ModelSelect2MultipleWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import GroupeCollaborateurs, Utilisateur


class Widget_utilisateur(ModelSelect2MultipleWidget):
    search_fields = ["last_name__icontains", "first_name__icontains", "username__icontains"]

    def label_from_instance(widget, instance):
        label = instance.get_full_name() or instance.username or instance.get_short_name()
        return label


class Formulaire(FormulaireBase, ModelForm):
    superviseurs = forms.ModelMultipleChoiceField(label="Superviseurs", widget=Widget_utilisateur({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
                                               queryset=Utilisateur.objects.none(), required=True)

    class Meta:
        model = GroupeCollaborateurs
        fields = "__all__"
        help_texts = {
            "nom": "Saisissez un nom pour ce groupe de collaborateurs. Ex: Equipe de direction...",
            "superviseurs": "Sélectionnez le ou les utilisateurs autorisés à accéder aux données des collaborateurs associés à ce groupe",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'groupes_collaborateurs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        self.fields["superviseurs"].queryset = Utilisateur.objects.filter(categorie="utilisateur").order_by("last_name", "first_name")

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'groupes_collaborateurs_liste' %}"),
            Field("nom"),
            Field("superviseurs"),
        )
