# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
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

        # Création des champs, regroupés par catégorie de questions
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        dict_groupes = {}
        for question in QuestionnaireQuestion.objects.select_related("groupe").filter(condition_structure, categorie="consommation", visible=True).order_by("groupe__ordre", "ordre"):
            if evenement.categorie and question.pk in [int(idq) for idq in evenement.categorie.questions.split(";")]:
                nom_controle, ctrl = questionnaires.Get_controle(question)
                if ctrl:
                    self.fields[nom_controle] = ctrl
                    dict_groupes.setdefault(question.groupe_id, {"nom": question.groupe.nom if question.groupe else None, "champs": []})
                    dict_groupes[question.groupe_id]["champs"].append(nom_controle)

        # Affichage
        self.helper.layout = Layout()
        for infos_groupe in dict_groupes.values():
            champs_layout = [Field(nom_controle) for nom_controle in infos_groupe["champs"]]
            if infos_groupe["nom"]:
                self.helper.layout.append(Fieldset(infos_groupe["nom"], *champs_layout))
            else:
                for champ in champs_layout:
                    self.helper.layout.append(champ)
        self.helper.layout.append(Hidden("idevenement", None))

    def clean(self):
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)
        return self.cleaned_data
