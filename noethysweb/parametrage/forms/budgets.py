# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Div
from crispy_forms.bootstrap import Field, PrependedText
from core.forms.select2 import Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences
from core.models import ComptaBudget, ComptaAnalytique, ComptaCategorieBudget, ComptaCategorie
from core.widgets import DatePickerWidget, Formset


class CategorieForm(FormulaireBase, forms.ModelForm):
    class Meta:
        model = ComptaCategorieBudget
        exclude = []

    def __init__(self, *args, **kwargs):
        super(CategorieForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

        # Catégories
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        self.fields["categorie"].queryset = ComptaCategorie.objects.filter(condition_structure).order_by("nom")
        self.fields["categorie"].label_from_instance = self.label_from_instance

        self.helper.layout = Layout(
            Field("categorie"),
            PrependedText("montant", utils_preferences.Get_symbole_monnaie()),
        )

    @staticmethod
    def label_from_instance(instance):
        return "%s (%s)" % (instance.nom, instance.get_type_display())

    def clean(self):
        return self.cleaned_data


class BaseCategorieFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(BaseCategorieFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        for form in self.forms:
            if not self._should_delete_form(form):
                # Vérification de la validité de la ligne
                if not form.is_valid() or len(form.cleaned_data) == 0:
                    for field, erreur in form.errors.as_data().items():
                        message = erreur[0].message
                        form.add_error(field, message)
                        return


FORMSET_CATEGORIES = inlineformset_factory(ComptaBudget, ComptaCategorieBudget, form=CategorieForm, fk_name="budget", formset=BaseCategorieFormSet,
                                            fields=["categorie", "montant"], extra=1, min_num=0,
                                            can_delete=True, validate_max=True, can_order=False)


class Formulaire(FormulaireBase, ModelForm):
    analytiques = forms.ModelMultipleChoiceField(label="Postes analytiques", widget=Select2MultipleWidget(), queryset=ComptaAnalytique.objects.all(), required=True)

    class Meta:
        model = ComptaBudget
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
            "date_debut": DatePickerWidget(),
            "date_fin": DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "budgets_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Analytiques
        condition_structure = Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        self.fields["analytiques"].queryset = ComptaAnalytique.objects.filter(condition_structure).order_by("nom")

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'budgets_liste' %}"),
            Fieldset("Généralités",
                Field("nom"),
                Field("observations"),
                Field("analytiques"),
            ),
            Fieldset("Période",
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset('Structure associée',
                Field('structure'),
            ),
            Fieldset("Catégories budgétaires",
                Div(
                    Formset("formset_categories"),
                    style="margin-bottom:20px;"
                ),
            ),
        )
