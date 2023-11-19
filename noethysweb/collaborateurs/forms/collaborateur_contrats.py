# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.select2 import Select2Widget
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import ContratCollaborateur, QuestionnaireQuestion, QuestionnaireReponse
from core.widgets import DatePickerWidget
from parametrage.forms import questionnaires


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = ContratCollaborateur
        fields = "__all__"
        widgets = {
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
            "type_poste": Select2Widget({"data-minimum-input-length": 0}),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "type_poste": "Sélectionnez le type de poste dans la liste proposée.",
            "date_debut": "Saisissez la date de début du contrat.",
            "date_fin": "Saisissez la date de fin de contrat ou laissez vide s'il s'agit d'un contrat à durée indéterminée."
        }

    def __init__(self, *args, **kwargs):
        idcollaborateur = kwargs.pop("idcollaborateur", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'collaborateurs_contrats_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('collaborateur', value=idcollaborateur),
            Fieldset("Généralités",
                Field("type_poste"),
                Field("observations"),
            ),
            Fieldset("Période",
                Field("date_debut"),
                Field("date_fin"),
            ),
        )

        # Création des champs des questionnaires
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        questions = QuestionnaireQuestion.objects.filter(condition_structure, categorie="contrat_collaborateur", visible=True).order_by("ordre")
        if questions:
            liste_fields = []
            for question in questions:
                nom_controle, ctrl = questionnaires.Get_controle(question)
                if ctrl:
                    self.fields[nom_controle] = ctrl
                    liste_fields.append(Field(nom_controle))
            self.helper.layout.append(Fieldset("Questionnaire", *liste_fields))

            # Importation des réponses
            for reponse in QuestionnaireReponse.objects.filter(donnee=self.instance.pk, question__categorie="contrat_collaborateur"):
                key = "question_%d" % reponse.question_id
                if key in self.fields:
                    self.fields[key].initial = reponse.Get_reponse_for_ctrl()

    def clean(self):
        # Période
        if self.cleaned_data["date_fin"] and self.cleaned_data["date_fin"] < self.cleaned_data["date_debut"]:
            self.add_error("date_fin", "La date de fin doit être supérieure à la date de début de contrat")
            return

        # Questionnaires
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)

        return self.cleaned_data

    def save(self):
        instance = super(Formulaire, self).save()

        # Enregistrement des réponses du questionnaire
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                idquestion = int(key.split("_")[1])
                QuestionnaireReponse.objects.update_or_create(donnee=instance.pk, question_id=idquestion, defaults={'reponse': valeur})

        return instance
