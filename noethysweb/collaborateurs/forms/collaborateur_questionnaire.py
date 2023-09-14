# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from core.forms.base import FormulaireBase
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import QuestionnaireQuestion, QuestionnaireReponse
from parametrage.forms import questionnaires


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        self.idcollaborateur = kwargs.pop("idcollaborateur")

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'collaborateur_questionnaire_form'
        self.helper.form_method = 'post'

        # self.helper.form_class = 'form-horizontal'
        # self.helper.label_class = 'col-md-2'
        # self.helper.field_class = 'col-md-10'

        # Création des champs
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        for question in QuestionnaireQuestion.objects.filter(condition_structure, categorie="collaborateur", visible=True).order_by("ordre"):
            nom_controle, ctrl = questionnaires.Get_controle(question)
            if ctrl:
                self.fields[nom_controle] = ctrl

        # Importation des réponses
        for reponse in QuestionnaireReponse.objects.filter(collaborateur_id=self.idcollaborateur):
            key = "question_%d" % reponse.question_id
            if key in self.fields:
                self.fields[key].initial = reponse.Get_reponse_for_ctrl()

        # Affichage
        self.helper.layout = Layout()

        if not self.fields:
            self.helper.layout.append(HTML("<strong>Aucun questionnaire n'a été paramétré.</strong>"))
        else:
            # Création des boutons de commande
            if self.mode == "CONSULTATION":
                commandes = Commandes(modifier_url="collaborateur_questionnaire_modifier", modifier_args="idcollaborateur=idcollaborateur", modifier=True,                                  enregistrer=False, annuler=False, ajouter=False)
                self.Set_mode_consultation()
            else:
                commandes = Commandes(annuler_url="{% url 'collaborateur_questionnaire' idcollaborateur=idcollaborateur %}", ajouter=False)
            self.helper.layout.append(commandes)
            # Création des contrôles
            for (nom_controle, ctrl) in self.fields.items():
                self.helper.layout.append(Field(nom_controle))

    def clean(self):
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)
        return self.cleaned_data
