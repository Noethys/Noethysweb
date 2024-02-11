# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.utils.translation import gettext as _
from crispy_forms.helper import FormHelper
from parametrage.forms import questionnaires
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        page = kwargs.pop("page", None)
        questions = kwargs.pop("questions", [])
        reponses = kwargs.pop("reponses", [])
        lecture_seule = kwargs.pop("lecture_seule", False)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "sondage_form"
        self.helper.form_method = "post"
        self.helper.form_tag = False

        # Création des champs
        for question in questions:
            if question.page_id == page.pk:
                nom_controle, ctrl = questionnaires.Get_controle(question)
                if ctrl:
                    self.fields[nom_controle] = ctrl
                    if question.obligatoire:
                        self.fields[nom_controle].required = True
                    if lecture_seule:
                        self.fields[nom_controle].disabled = True

        # Importation des réponses existantes
        for reponse in reponses:
            key = "question_%d" % reponse.question_id
            if key in self.fields:
                self.fields[key].initial = reponse.Get_reponse_for_ctrl()

    def clean(self):
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)
        return self.cleaned_data
