# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
import datetime
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset
from crispy_forms.bootstrap import Field, FormActions, PrependedText
from core.forms.select2 import Select2MultipleWidget
from core.models import Activite, TypeGroupeActivite


class Formulaire(FormulaireBase, ModelForm):
    # Groupes d'activités
    groupes_activites = forms.ModelMultipleChoiceField(label="Groupes d'activités", widget=Select2MultipleWidget(), queryset=TypeGroupeActivite.objects.all(), required=False,
                                                       help_text="""Sélectionnez un ou plusieurs groupes d'activités à associer à cette activité. Les groupes d'activités 
                                                       permettent d'effectuer des sélections rapides par 'famille d'activités' dans plusieurs fonctionnalités de l'application. 
                                                       Si aucun groupe d'activités n'est disponible, vous pouvez les créer depuis le menu Paramétrage > Groupes d'activités.""")

    class Meta:
        model = Activite
        fields = ["nom", "abrege", "groupes_activites", "date_debut", "date_fin", "structure"]
        help_texts = {
            "nom": "Saisissez le nom complet de l'activité. Exemples : Accueil de loisirs, Cantine, Club de yoga - Saison 2024-25, Séjour à la neige - Février 2024...",
            "abrege": "Saisissez le nom abrégé de l'activité (quelques caractères en majuscules). Exemples : ALSH, PERI, YOGA24, COLO, STAGE...",
            "structure": "Sélectionnez la structure associée à cette activité.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_generalites_form'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Field('nom'),
            Field('abrege'),
            Field("groupes_activites"),
            Field("structure"),
            Hidden('date_debut', value=datetime.date(1977, 1, 1)),
            Hidden('date_fin', value=datetime.date(2999, 1, 1)),
            FormActions(
                Submit('submit', 'Enregistrer', css_class='btn-primary'),
                HTML("""<a class="btn btn-danger" href="{% url 'activites_liste' %}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""))
        )
