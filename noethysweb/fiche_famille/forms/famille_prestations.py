# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder, Div
from crispy_forms.bootstrap import Field, StrictButton, PrependedText
from core.utils.utils_commandes import Commandes
from core.models import Famille, Prestation, Deduction
from core.widgets import DatePickerWidget, Formset
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from core.utils import utils_preferences



class DeductionForm(forms.ModelForm):

    class Meta:
        model = Deduction
        exclude = []

    def __init__(self, *args, **kwargs):
        super(DeductionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_show_labels = False

    def clean(self):
        # if self.cleaned_data.get('DELETE') == False:
        #
        #     # Vérifie qu'au moins une unité a été saisie
        #     if len(self.cleaned_data["unites"]) == 0:
        #         raise forms.ValidationError('Vous devez sélectionner au moins une unité')
        #
        return self.cleaned_data


class BaseDeductionFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super(BaseDeductionFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        for form in self.forms:
            if self._should_delete_form(form) == False:

                # Vérification de la validité de la ligne
                if form.is_valid() == False or len(form.cleaned_data) == 0:
                    for field, erreur in form.errors.as_data().items():
                        message = erreur[0].message
                        form.add_error(field, message)
                        return



FORMSET_DEDUCTIONS = inlineformset_factory(Prestation, Deduction, form=DeductionForm, fk_name="prestation", formset=BaseDeductionFormSet,
                                            fields=["montant", "label"], extra=0, min_num=1,
                                            can_delete=True, validate_max=True, can_order=False)



class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Prestation
        fields = "__all__"
        widgets = {
            'date': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_prestations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit la famille associée
        famille = Famille.objects.get(pk=idfamille)

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('famille', value=idfamille),
            Field('date'),
            Field('categorie'),
            Field('label'),
            Field('individu'),
            Field('activite'),
            Field('categorie_tarif'),
            Field('tarif'),
            Field('code_compta'),
            Field('code_produit_local'),
            PrependedText('montant_initial', utils_preferences.Get_symbole_monnaie()),
            PrependedText('montant', utils_preferences.Get_symbole_monnaie()),
            PrependedText('tva', '%'),
            Fieldset("Déductions",
                Div(
                    Div(
                        HTML("<label class='col-form-label col-md-2 requiredField'><b>Déductions</b></label>"),
                        Div(
                            Formset("formset_combi"),
                            css_class="controls col-md-10"
                        ),
                        css_class="form-group row"
                    ),
                ),
            ),
        )

    def clean(self):
        return self.cleaned_data

