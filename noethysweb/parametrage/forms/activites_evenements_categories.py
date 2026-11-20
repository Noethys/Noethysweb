# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, Div, HTML
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2MultipleWidget
from core.utils.utils_commandes import Commandes
from core.utils import utils_images
from core.models import CategorieEvenement, LimitationCategorieEvenement, Activite, QuestionnaireQuestion
from core.widgets import Crop_image, Formset


class LimitationForm(FormulaireBase, forms.ModelForm):
    class Meta:
        model = LimitationCategorieEvenement
        fields = ["nbre_max", "periode", "date_debut", "date_fin"]
        widgets = {
            "date_debut": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "date_fin": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super(LimitationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.fields["nbre_max"].widget.attrs.update({"min": 1, "max": 99})
        self.fields["periode"].widget.attrs.update({"class": "select_periode_limitation"})
        self.helper.layout = Layout(
            Field("nbre_max"),
            Field("periode"),
            Field("date_debut"),
            Field("date_fin"),
        )

    def clean(self):
        periode = self.cleaned_data.get("periode")
        date_debut, date_fin = self.cleaned_data.get("date_debut"), self.cleaned_data.get("date_fin")
        if periode == "PERIODE":
            if not date_debut or not date_fin:
                self.add_error("date_debut", "Vous devez saisir les dates de la période")
            elif date_debut > date_fin:
                self.add_error("date_fin", "La date de fin doit être supérieure à la date de début")
        else:
            self.cleaned_data["date_debut"] = None
            self.cleaned_data["date_fin"] = None
        return self.cleaned_data


class BaseLimitationFormSet(BaseInlineFormSet):
    def clean(self):
        for form in self.forms:
            if not self._should_delete_form(form):
                if not form.is_valid() or len(form.cleaned_data) == 0:
                    for field, erreur in form.errors.as_data().items():
                        form.add_error(field, erreur[0].message)
                        return


FORMSET_LIMITATIONS = inlineformset_factory(CategorieEvenement, LimitationCategorieEvenement, form=LimitationForm, fk_name="categorie", formset=BaseLimitationFormSet,
                                            fields=["nbre_max", "periode", "date_debut", "date_fin"], extra=1, min_num=0,
                                            can_delete=True, validate_max=True, can_order=False)


class Formulaire(FormulaireBase, ModelForm):
    cropper_data = forms.CharField(widget=forms.HiddenInput(), required=False)
    selection_questions = forms.MultipleChoiceField(label="Questions", widget=Select2MultipleWidget(), choices=[], required=False,
                                          help_text="Vous pouvez sélectionner les questions d'un questionnaire de type 'Consommation'. Lorsqu'un individu saisira un événement dans la grille des consommations, ces questions seront posées et associées à la consommation.")

    class Meta:
        model = CategorieEvenement
        fields = "__all__"
        widgets = {
            "image": Crop_image(attrs={"largeur_min": 400, "hauteur_min": 100, "ratio": "400/100"}),
        }
        help_texts = {
            "image": "Vous pouvez sélectionner une image à appliquer sur l'arrière-plan de la case des événements liés dans la grille des consommations. L'image sera convertie en niveaux de gris à l'affichage.",
            "nom": "Saisissez le nom de la catégorie d'événements. Exemples : Sorties, Ateliers, Spectacles, Mini-camps...",
        }

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_evenements_categories_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "activite") == False:
            activite = Activite.objects.get(pk=idactivite)
        else:
            activite = self.instance.activite

        # Questions
        questions = QuestionnaireQuestion.objects.filter(categorie="consommation").order_by("ordre")
        self.fields["selection_questions"].choices = [(question.pk, question.label) for question in questions]
        if self.instance.questions:
            self.fields["selection_questions"].initial = [int(idquestion) for idquestion in self.instance.questions.split(";")]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden("activite", value=activite.idactivite),
            Field("cropper_data"),
            Fieldset("Généralités",
                Field("nom"),
            ),
            Fieldset("Image d'arrière-plan",
                Field("image"),
            ),
            Fieldset("Questionnaire",
                Field("selection_questions"),
            ),
            Fieldset("Limitations des réservations",
                HTML(HTML_AIDE_LIMITATIONS),
                Div(
                    Formset("formset_limitations"),
                    style="margin-bottom:20px;"
                ),
                HTML(JS_LIMITATIONS),
            ),
        )

    def save(self):
        form = super(Formulaire, self).save()
        cropper_data = self.cleaned_data.get("cropper_data")
        if cropper_data:
            utils_images.Recadrer_image_form(cropper_data, form.image)
        return form

    def clean(self):
        # Questions
        if self.cleaned_data["selection_questions"]:
            self.cleaned_data["questions"] = ";".join(self.cleaned_data["selection_questions"])
        else:
            self.cleaned_data["questions"] = None
        return self.cleaned_data


HTML_AIDE_LIMITATIONS = """
<p class="text-muted" style="margin-bottom: 5px;">
    Vous pouvez limiter le nombre d'événements de cette catégorie qu'un individu peut réserver sur une période. Toutes les règles s'appliquent simultanément.
    Toutes les réservations de l'individu sur les événements de cette catégorie sont comptées, quel que soit leur état (réservation, attente, refus...).
    Sur le portail, une réservation qui dépasse une limite est refusée. Dans les grilles de saisie, un simple avertissement est affiché.
    La semaine va du lundi au dimanche, l'année est l'année civile.
</p>
"""

JS_LIMITATIONS = """
<script>
    function maj_periode_limitation(select) {
        var ligne = $(select).closest("tr");
        var actif = $(select).val() === "PERIODE";
        ligne.find("input[type='date']").prop("disabled", !actif);
        if (!actif) {ligne.find("input[type='date']").val("")};
    };
    $(document).on("change", ".select_periode_limitation", function () {maj_periode_limitation(this)});
    $(function () {$(".select_periode_limitation").each(function () {maj_periode_limitation(this)})});
    function formset_apres_ajout(row) {
        row.find(".select_periode_limitation").val("SEMAINE");
        maj_periode_limitation(row.find(".select_periode_limitation"));
    };
</script>
"""
