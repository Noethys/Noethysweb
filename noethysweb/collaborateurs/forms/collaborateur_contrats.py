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
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import ContratCollaborateur, QuestionnaireQuestion, QuestionnaireReponse
from core.widgets import DatePickerWidget
from parametrage.forms import questionnaires


JOURS_SEMAINE_CONTRAT = [("0", "Lundi"), ("1", "Mardi"), ("2", "Mercredi"), ("3", "Jeudi"), ("4", "Vendredi"), ("5", "Samedi"), ("6", "Dimanche")]


class Formulaire(FormulaireBase, ModelForm):
    jours_travailles = forms.MultipleChoiceField(label="Jours travaillés", choices=JOURS_SEMAINE_CONTRAT, widget=forms.CheckboxSelectMultiple, required=True,
                                                 help_text="Cochez les jours habituellement travaillés. Ils servent à poser les absences et à décompter les congés "
                                                           "(par exemple du lundi au jeudi pour un 4/5e qui ne travaille pas le vendredi).")

    class Meta:
        model = ContratCollaborateur
        fields = "__all__"
        widgets = {
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
            "type_contrat": Select2Widget({"data-minimum-input-length": 0}),
            "type_poste": Select2Widget({"data-minimum-input-length": 0}),
            "modele_planning": Select2Widget({"data-minimum-input-length": 0}),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "type_contrat": "Sélectionnez le type de contrat (CDI, CDD, titulaire...). La liste se paramètre dans Paramétrage > Types de contrats.",
            "type_poste": "Sélectionnez le poste occupé (animateur, directeur...). La liste se paramètre dans Paramétrage > Types de postes.",
            "date_debut": "Saisissez la date de début du contrat au format JJ/MM/AAAA.",
            "date_fin": "Saisissez la date de fin du contrat au format JJ/MM/AAAA. Laissez vide pour un contrat à durée indéterminée.",
            "heures_hebdo": "Nombre d'heures prévues par semaine (exemple : 35, ou 28 pour un 4/5e). Il sert au calcul de l'objectif de temps de travail "
                            "(mode hebdomadaire, ou quotité en mode annualisé), aux heures « prévues au contrat » du planning et à la durée d'une journée pour les congés. "
                            "Il est réparti sur les jours travaillés cochés ci-dessous.",
            "modele_planning": "Facultatif. À la création du contrat, il vous sera proposé de l'appliquer sur la période du contrat. Il est aussi présélectionné dans l'outil « Appliquer un modèle ».",
            "observations": "Saisissez si besoin une remarque sur ce contrat. Elle peut être reprise dans un document Word avec le champ {CONTRAT_OBSERVATIONS}."
        }

    def __init__(self, *args, **kwargs):
        idcollaborateur = kwargs.pop("idcollaborateur", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        # Jours travaillés : lundi au vendredi par défaut. La valeur enregistrée ("0,1,2,3,4") est convertie en liste pour cocher les cases.
        jours = (self.instance.jours_travailles or "0,1,2,3,4").split(",")
        self.fields["jours_travailles"].initial = jours
        self.initial["jours_travailles"] = jours

        # Tri alphabétique des listes déroulantes
        for nom_champ in ("type_contrat", "type_poste", "profil_reglementaire", "modele_planning"):
            self.fields[nom_champ].queryset = self.fields[nom_champ].queryset.order_by("nom")

        # Modèles de planning : nom, durée du cycle et heures par semaine
        from collaborateurs.utils import utils_modeles_planning, utils_objectif
        infos = {modele["id"]: modele for modele in utils_modeles_planning.Get_liste_modeles()["modeles"]}
        def Libelle_modele(modele):
            info = infos.get(modele.pk)
            return "%s (%s · %s par semaine)" % (modele.nom, info["cycle"], utils_objectif.Format_heures(info["heures"])) if info else modele.nom
        self.fields["modele_planning"].label_from_instance = Libelle_modele

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
                Field("type_contrat"),
                Field("type_poste"),
                Field("observations"),
            ),
            Fieldset("Période",
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset("Temps de travail",
                Field("heures_hebdo"),
                InlineCheckboxes("jours_travailles", template="collaborateurs/champ_cases_en_ligne.html"),
                Field("modele_planning"),
                Field("profil_reglementaire"),
            ),
            Fieldset("Objectif de temps de travail",
                Field("objectif_mode"),
                Field("objectif_volume"),
                Field("objectif_periode"),
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
        # Objectif
        if self.cleaned_data.get("objectif_mode") == "VOLUME" and not self.cleaned_data.get("objectif_volume"):
            self.add_error("objectif_volume", "Saisissez le nombre d'heures prévues pour ce contrat")
            return
        if self.cleaned_data.get("objectif_volume") is not None and self.cleaned_data["objectif_volume"] <= 0:
            self.add_error("objectif_volume", "Le volume de référence doit être supérieur à zéro")
            return

        # Période
        if self.cleaned_data["date_fin"] and self.cleaned_data["date_fin"] < self.cleaned_data["date_debut"]:
            self.add_error("date_fin", "La date de fin doit être supérieure à la date de début de contrat")
            return

        # Jours travaillés
        self.cleaned_data["jours_travailles"] = ",".join(sorted(self.cleaned_data.get("jours_travailles") or []))
        if not self.cleaned_data["jours_travailles"]:
            self.add_error("jours_travailles", "Cochez au moins un jour travaillé")
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
