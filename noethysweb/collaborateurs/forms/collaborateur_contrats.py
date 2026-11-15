# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.select2 import Select2Widget
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, HTML
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import ContratCollaborateur, QuestionnaireQuestion, QuestionnaireReponse
from core.widgets import DatePickerWidget
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from parametrage.forms import questionnaires


# Champs repris du précédent contrat lors de la création d'un nouveau contrat (dates et observations exclues)
CHAMPS_REPRIS = ["type_contrat", "type_poste", "heures_hebdo", "jours_travailles", "modele_planning", "profil_reglementaire", "objectif_mode", "objectif_volume", "objectif_periode"]

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

        # Création d'un contrat : reprise des données du précédent contrat du collaborateur (sauf dates et observations)
        self.contrat_precedent = None
        if not self.instance.pk and idcollaborateur and not (self.request and self.request.GET.get("vierge")):
            self.contrat_precedent = ContratCollaborateur.objects.select_related("type_contrat", "type_poste").filter(collaborateur_id=idcollaborateur).order_by("-date_debut", "-pk").first()
        if self.contrat_precedent:
            for nom_champ in CHAMPS_REPRIS:
                champ_modele = ContratCollaborateur._meta.get_field(nom_champ)
                self.initial[nom_champ] = getattr(self.contrat_precedent, champ_modele.attname)

        # Jours travaillés : lundi au vendredi par défaut. La valeur enregistrée ("0,1,2,3,4") est convertie en liste pour cocher les cases.
        jours = ((self.contrat_precedent or self.instance).jours_travailles or "0,1,2,3,4").split(",")
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
            *self.Get_bandeau_reprise(),
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

            # Importation des réponses (celles du précédent contrat lors d'une création)
            iddonnee = self.instance.pk or (self.contrat_precedent.pk if self.contrat_precedent else None)
            for reponse in QuestionnaireReponse.objects.filter(donnee=iddonnee, question__categorie="contrat_collaborateur") if iddonnee else []:
                key = "question_%d" % reponse.question_id
                if key in self.fields:
                    self.fields[key].initial = reponse.Get_reponse_for_ctrl()

    def Get_bandeau_reprise(self):
        """ Bandeau signalant que les données du précédent contrat ont été reproduites """
        contrat = self.contrat_precedent
        if not contrat:
            return []
        libelle = " · ".join([nom for nom in (contrat.type_poste.nom, contrat.type_contrat.nom if contrat.type_contrat else None) if nom])
        periode = "du %s au %s" % (contrat.date_debut.strftime("%d/%m/%Y"), contrat.date_fin.strftime("%d/%m/%Y")) if contrat.date_fin else "depuis le %s" % contrat.date_debut.strftime("%d/%m/%Y")
        texte = format_html("Les données du précédent contrat ({} · {}) ont été reproduites. Vérifiez-les avant d'enregistrer.", libelle, periode)
        if not contrat.date_fin:
            texte += mark_safe(" <br>Ce précédent contrat n'a pas de date de fin : pensez à le clôturer pour éviter un chevauchement des deux contrats.")
        html = format_html("""<div class="alert alert-info d-flex align-items-center justify-content-between flex-wrap" role="status">
            <span class="mr-2"><i class="fa fa-info-circle mr-1" aria-hidden="true"></i>{}</span>
            <a href="?vierge=1" class="btn btn-sm btn-light mt-1 mb-1"><i class="fa fa-eraser mr-1" aria-hidden="true"></i>Vider le formulaire</a>
        </div>""", texte)
        # Le bloc HTML de crispy est interprété comme un template Django : neutralisation des accolades éventuelles des libellés
        return [HTML(html.replace("{", "&#123;").replace("}", "&#125;"))]

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
