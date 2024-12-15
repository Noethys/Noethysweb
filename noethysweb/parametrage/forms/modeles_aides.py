# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, PrependedText, InlineCheckboxes
from core.forms.select2 import Select2MultipleWidget
from core.widgets import DatePickerWidget, Formset, Select_activite
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences
from core.utils.utils_texte import Creation_tout_cocher
from core.models import Activite, Aide, JOURS_SEMAINE


class Formulaire_creation(FormulaireBase, forms.Form):
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection de l'activité",
                Field("activite"),
            ),
        )


class Formulaire(FormulaireBase, ModelForm):
    montant_max = forms.DecimalField(label="Montant plafond", max_digits=6, decimal_places=2, initial=0.0, required=False)
    jours_scolaires = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_scolaires"))
    jours_vacances = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_vacances"))

    # Champ fictif nécessire pour charger Select2MultipleWidget pour le formset
    champ_fictif = forms.ModelMultipleChoiceField(label="Champ fictif", widget=Select2MultipleWidget(), queryset=Aide.objects.none(), required=False)

    class Meta:
        model = Aide
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        activite = kwargs.pop("activite", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_aides_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-form-label col-md-2'
        self.helper.field_class = 'col-md-10'

        # Activité
        self.fields["activite"].disabled = True
        if not self.instance.pk:
            self.fields["activite"].initial = activite

        # Jours
        self.fields["jours_scolaires"].initial = [0, 1, 2, 3, 4]
        self.fields["jours_vacances"].initial = [0, 1, 2, 3, 4]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_aides_liste' %}"),
            Fieldset("Généralités",
                Field('activite'),
                Field('nom'),
                Field('caisse'),
                Field('date_debut'),
                Field('date_fin'),
            ),
            Fieldset("Montants",
                Div(
                    Div(
                        HTML("<label class='col-form-label col-md-2 requiredField'><b>Montants*</b></label>"),
                        Div(
                            Formset("formset_combi"),
                            css_class="controls col-md-10"
                        ),
                        css_class="form-group row"
                    ),
                ),
            ),
            Fieldset("Options",
                InlineCheckboxes('jours_scolaires'),
                InlineCheckboxes('jours_vacances'),
                PrependedText('montant_max', utils_preferences.Get_symbole_monnaie()),
                Field('nbre_dates_max'),
            ),
        )
