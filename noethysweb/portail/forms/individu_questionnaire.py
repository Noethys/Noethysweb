# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.models import Individu, QuestionnaireQuestion, QuestionnaireReponse, PortailRenseignement
from parametrage.forms import questionnaires
from portail.forms.fiche import FormulaireBase
import json


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        rattachement = kwargs.pop("rattachement", None)
        mode = kwargs.pop("mode", "CONSULTATION")
        individu = kwargs.pop("instance", None)

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_questionnaire_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # self.helper.use_custom_control = False

        # Importation des renseignements en attente de validation
        renseignements = PortailRenseignement.objects.filter(categorie="individu_questionnaire", famille=rattachement.famille, individu=rattachement.individu, etat="ATTENTE", validation_auto=False).order_by("date")
        dict_renseignements = {renseignement.code: json.loads(renseignement.nouvelle_valeur) for renseignement in renseignements}

        # Création des champs
        for question in QuestionnaireQuestion.objects.filter(categorie="individu", visible_portail=True).order_by("ordre"):
            nom_controle, ctrl = questionnaires.Get_controle(question)
            if ctrl:
                self.fields[nom_controle] = ctrl

        # Importation des réponses
        for reponse in QuestionnaireReponse.objects.filter(individu=rattachement.individu, question__categorie="individu"):
            key = "question_%d" % reponse.question_id
            if key in self.fields:
                self.fields[key].initial = reponse.Get_reponse_for_ctrl()

        # Préparation du layout
        self.helper.layout = Layout()
        for (code, ctrl) in self.fields.items():
            # Si mode consultation
            if mode == "CONSULTATION":
                self.fields[code].disabled = True
                self.fields[code].help_text = None
            # Intégration des valeurs en attente de validation par l'admin
            if code in dict_renseignements and self.fields[code].initial != dict_renseignements[code]:
                self.fields[code].initial = dict_renseignements[code]
                self.fields[code].help_text = "<span class='text-orange'><i class='fa fa-exclamation-circle margin-r-5'></i>Modification en attente de validation par l'administrateur.</span>"
            self.helper.layout.append(Field(code, css_class="text-orange" if code in dict_renseignements else None))

        if not self.fields:
            # Si aucun questionnaire paramétré
            self.helper.layout.append(HTML("<strong>Aucun questionnaire n'a été paramétré.</strong>"))
        else:
            # Ajout des commandes
            if mode == "CONSULTATION":
                self.helper.layout.append(ButtonHolder(HTML("""<a class="btn btn-primary" href="{% url 'portail_individu_questionnaire_modifier' idrattachement=rattachement.pk %}" title="Modifier"><i class="fa fa-pencil margin-r-5"></i>Modifier cette page</a>"""), css_class="pull-right"))
            if mode == "EDITION":
                self.helper.layout.append(ButtonHolder(
                        StrictButton("<i class='fa fa-check margin-r-5'></i>Enregistrer les modifications", title="Enregistrer", name="enregistrer", type="submit", css_class="btn-primary"),
                        HTML("""<a class="btn btn-danger" href='{% url 'portail_individu_questionnaire' idrattachement=rattachement.pk %}' title="Annuler"><i class="fa fa-ban margin-r-5"></i>Annuler</a>"""),
                        css_class="pull-right"))

    def clean(self):
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)
        return self.cleaned_data
