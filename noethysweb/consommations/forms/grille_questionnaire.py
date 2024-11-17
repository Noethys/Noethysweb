# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import QuestionnaireQuestion, Evenement
from parametrage.forms import questionnaires


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        idevenement = kwargs.pop("idevenement", 0)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "grille_form_questionnaire"
        self.helper.form_method = "post"

        # Importation des questions de la catégorie d'événement
        evenement = Evenement.objects.select_related("categorie").get(pk=idevenement)

        # Création des champs
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        for question in QuestionnaireQuestion.objects.filter(condition_structure, categorie="consommation", visible=True).order_by("ordre"):
            if evenement.categorie and question.pk in [int(idq) for idq in evenement.categorie.questions.split(";")]:
                nom_controle, ctrl = questionnaires.Get_controle(question)
                if ctrl:
                    self.fields[nom_controle] = ctrl

        # Affichage
        self.helper.layout = Layout()
        for (nom_controle, ctrl) in self.fields.items():
            self.helper.layout.append(Field(nom_controle))
        self.helper.layout.append(Hidden("idevenement", None))

    def clean(self):
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)
        return self.cleaned_data
