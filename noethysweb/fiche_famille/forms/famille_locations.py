# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django_select2.forms import ModelSelect2Widget, Select2Widget
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, InlineCheckboxes
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils.utils_texte import Creation_tout_cocher
from core.models import Location, QuestionnaireQuestion, QuestionnaireReponse, Produit, Prestation, JOURS_SEMAINE, Famille
from core.widgets import DatePickerWidget, DateTimePickerWidget, Formset
from parametrage.forms import questionnaires


class PrestationForm(forms.ModelForm):
    class Meta:
        model = Prestation
        exclude = []
        widgets = {
            "date": DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(PrestationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

    def clean(self):
        return self.cleaned_data


class BasePrestationFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(BasePrestationFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        for form in self.forms:
            if not self._should_delete_form(form):
                # Vérification de la validité de la ligne
                if not form.is_valid() or len(form.cleaned_data) == 0:
                    for field, erreur in form.errors.as_data().items():
                        message = erreur[0].message
                        form.add_error(field, message)
                        return


FORMSET_PRESTATIONS = inlineformset_factory(Location, Prestation, form=PrestationForm, fk_name="location", formset=BasePrestationFormSet,
                                            fields=["date", "label", "montant", "tva"], extra=1, min_num=0,
                                            can_delete=True, validate_max=True, can_order=False)


class Widget_modele(ModelSelect2Widget):
    search_fields = ["label__icontains"]

    def label_from_instance(widget, instance):
        return "%s - %s" % (instance.nom, instance.categorie.nom)


class Formulaire(FormulaireBase, ModelForm):
    # Famille
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
                                     queryset=Famille.objects.all().order_by("nom"), required=True)
    # Produit
    produit = forms.ModelChoiceField(label="Produit", widget=Widget_modele({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
                                     queryset=Produit.objects.select_related("categorie").all(), required=True)

    # Période
    choix_periode = [("UNIQUE", "Période unique"), ("RECURRENCE", "Récurrence")]
    selection_periode = forms.TypedChoiceField(label="Type de période", choices=choix_periode, initial="UNIQUE", required=False)
    recurrence_date_debut = forms.DateField(label="Date de début", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    recurrence_date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    recurrence_heure_debut = forms.TimeField(label="Heure de début", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    recurrence_heure_fin = forms.TimeField(label="Heure de fin", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    recurrence_feries = forms.BooleanField(label="Inclure les fériés", required=False)
    recurrence_jours_scolaires = forms.MultipleChoiceField(label="Jours scolaires", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("recurrence_jours_scolaires"))
    recurrence_jours_vacances = forms.MultipleChoiceField(label="Jours de vacances", required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("recurrence_jours_vacances"))
    choix_frequence = [(1, "Toutes les semaines"), (2, "Une semaine sur deux"),
                        (3, "Une semaine sur trois"), (4, "Une semaine sur quatre"),
                        (5, "Les semaines paires"), (6, "Les semaines impaires")]
    recurrence_frequence_type = forms.TypedChoiceField(label="Fréquence", choices=choix_frequence, initial=1, required=False)

    class Meta:
        model = Location
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
            "date_debut": DateTimePickerWidget(),
            "date_fin": DateTimePickerWidget(),
        }
        help_texts = {
            "date_debut": "Saisissez une date et heure de début au format JJ/MM/AAAA HH:MM.",
            "date_fin": "Saisissez une date et heure de début au format JJ/MM/AAAA HH:MM ou laissez vide pour une location sans durée définie.",
        }

    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_id = 'famille_locations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        if self.idfamille or self.instance.pk:
            self.fields["famille"].initial = self.idfamille
            self.fields["famille"].widget.attrs["disabled"] = "disabled"
            self.fields["famille"].disabled = True

        self.fields["date_debut"].initial = datetime.datetime.now()
        self.fields["recurrence_jours_scolaires"].initial = [0, 1, 2, 3, 4]
        self.fields["recurrence_jours_vacances"].initial = [0, 1, 2, 3, 4]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('idlocation', value=self.instance.pk if self.instance else None),
            Fieldset("Généralités",
                Field("famille"),
                Field("produit"),
                Field("observations"),
            ),
            Fieldset("Période de location",
                Field("selection_periode"),
                Div(
                    Field("date_debut"),
                    Field("date_fin"),
                    id="div_periode_unique",
                ),
                Div(
                    Field("recurrence_date_debut"),
                    Field("recurrence_date_fin"),
                    Field("recurrence_feries"),
                    Field("recurrence_heure_debut"),
                    Field("recurrence_heure_fin"),
                    InlineCheckboxes("recurrence_jours_scolaires"),
                    InlineCheckboxes("recurrence_jours_vacances"),
                    Field("recurrence_frequence_type"),
                    id="div_periode_recurrente",
                ),
            ),
            Fieldset("Quantité",
                Field("quantite"),
            ),
            Fieldset("Prestations",
                Div(
                    Formset("formset_prestations"),
                    HTML("""<button type="button" class="btn btn-default btn-sm btn-block" onclick="appliquer_tarif()"><i class="fa fa-bolt margin-r-5"></i>Appliquer un tarif prédéfini</button>"""),
                    style="margin-bottom:20px;"
                ),
            ),
        )

        # Intégration des commandes pour le mode planning
        if not self.idfamille:
            commandes = Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False, autres_commandes=[
                HTML("""<button type="submit" name="enregistrer" title="Enregistrer" class="btn btn-primary"><i class="fa fa-check margin-r-5"></i>Enregistrer</button> """),
                HTML("""<a class="btn btn-danger" title="Annuler" onclick="$('#modal_detail_location').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """),
            ],)
            if self.instance.pk:
                commandes.insert(1, HTML("""<button type="button" class="btn btn-warning" onclick="supprimer_location(%d)"><i class="fa fa-trash margin-r-5"></i>Supprimer</button> """ % self.instance.pk))
            self.helper.layout[0] = commandes

        # Création des champs des questionnaires
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        questions = QuestionnaireQuestion.objects.filter(condition_structure, categorie="location", visible=True).order_by("ordre")
        if questions:
            liste_fields = []
            for question in questions:
                nom_controle, ctrl = questionnaires.Get_controle(question)
                if ctrl:
                    self.fields[nom_controle] = ctrl
                    liste_fields.append(Field(nom_controle))
            self.helper.layout.append(Fieldset("Questionnaire", *liste_fields))

            # Importation des réponses
            for reponse in QuestionnaireReponse.objects.filter(donnee=self.instance.pk, question__categorie="location"):
                key = "question_%d" % reponse.question_id
                if key in self.fields:
                    self.fields[key].initial = reponse.Get_reponse_for_ctrl()

    def clean(self):
        # Questionnaires
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                if isinstance(valeur, list):
                    self.cleaned_data[key] = ";".join(valeur)

        # Période de location
        if self.cleaned_data["selection_periode"] == "UNIQUE":
            if self.cleaned_data["date_fin"] and self.cleaned_data["date_fin"] < self.cleaned_data["date_debut"]:
                self.add_error("date_fin", "La date de fin doit être supérieure à la date de début")
                return

        if self.cleaned_data["selection_periode"] == "UNIQUE":
            if not self.cleaned_data["date_debut"]:
                self.add_error("date_debut", "Vous devez sélectionner une date de début")
                return

        if self.cleaned_data["selection_periode"] == "RECURRENCE":
            for code, label in [("date_debut", "date de début"), ("date_fin", "date de fin"), ("heure_debut", "heure de début"), ("heure_fin", "heure de fin")]:
                if not self.cleaned_data["recurrence_%s" % code]:
                    self.add_error("recurrence_%s" % code, "Vous devez sélectionner une %s" % label)
                    return

        return self.cleaned_data

    def save(self):
        instance = super(Formulaire, self).save()

        # Enregistrement des réponses du questionnaire
        for key, valeur in self.cleaned_data.items():
            if key.startswith("question_"):
                idquestion = int(key.split("_")[1])
                QuestionnaireReponse.objects.update_or_create(donnee=instance.pk, question_id=idquestion, defaults={'reponse': valeur})

        return instance
