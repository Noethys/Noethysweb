# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django import forms
from django.utils.translation import gettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.models import QuestionnaireQuestion, QuestionnaireReponse, PortailRenseignement
from parametrage.forms import questionnaires
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    def __init__(self, *args, **kwargs):
        rattachement = kwargs.pop("rattachement", None)
        mode = kwargs.pop("mode", "CONSULTATION")
        individu = kwargs.pop("instance", None)

        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_questionnaire_form'
        self.helper.form_method = 'post'

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
                self.fields[code].help_text = "<span class='text-orange'><i class='fa fa-exclamation-circle margin-r-5'></i>%s</span>" % _("Modification en attente de validation par l'administrateur.")
            self.helper.layout.append(Field(code, css_class="text-orange" if code in dict_renseignements else None))

        if not self.fields:
            # Si aucun questionnaire paramétré
            self.helper.layout.append(HTML("<strong>%s</strong>" % _("Aucun questionnaire n'a été paramétré.")))
        else:
            # Ajout des commandes
            if mode == "CONSULTATION":
                self.helper.layout.append(ButtonHolder(HTML("""<a class="btn btn-primary" href="{{% url 'portail_individu_questionnaire_modifier' idrattachement=rattachement.pk %}}" title="{title}"><i class="fa fa-pencil margin-r-5"></i>{label}</a>""".format(title=_("Modifier"), label=_("Modifier cette page"))), css_class="pull-right"))
            if mode == "EDITION":
                self.helper.layout.append(ButtonHolder(
                        StrictButton("<i class='fa fa-check margin-r-5'></i>%s" % _("Enregistrer les modifications"), title=_("Enregistrer"), name="enregistrer", type="submit", css_class="btn-primary"),
                        HTML("""<a class="btn btn-danger" href='{{% url 'portail_individu_questionnaire' idrattachement=rattachement.pk %}}' title="{title}"><i class="fa fa-ban margin-r-5"></i>{label}</a>""".format(title=_("Annuler"), label=_("Annuler"))), css_class="pull-right"))

    def clean(self):
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)
        return self.cleaned_data
