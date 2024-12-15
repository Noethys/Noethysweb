# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django_select2.forms import Select2MultipleWidget, ModelSelect2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder, Div
from crispy_forms.bootstrap import Field, PrependedText, InlineCheckboxes
from core.forms.base import FormulaireBase
from core.models import Aide, JOURS_SEMAINE, Rattachement, Individu, CombiAide, Unite, Activite
from core.widgets import DatePickerWidget, Formset, Select_activite
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences
from core.utils.utils_texte import Creation_tout_cocher


class CombiAideForm(forms.ModelForm):
    unites = forms.ModelMultipleChoiceField(label="Combinaison conditionnelle d'unités", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), queryset=Unite.objects.none(), required=False)

    class Meta:
        model = CombiAide
        exclude = []

    def __init__(self, *args, activite, **kwargs):
        super(CombiAideForm, self).__init__(*args, **kwargs)
        self.activite = activite

        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.fields['unites'].queryset = Unite.objects.filter(activite=activite)

    def clean(self):
        if self.cleaned_data.get('DELETE') == False:

            # Vérifie qu'au moins une unité a été saisie
            if len(self.cleaned_data["unites"]) == 0:
                raise forms.ValidationError('Vous devez sélectionner au moins une unité')

        return self.cleaned_data


class BaseCombiAideFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.activite = kwargs.get("activite", None)
        super(BaseCombiAideFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        index_ligne = 0
        liste_lignes_unites = []
        for form in self.forms:
            if self._should_delete_form(form) == False:

                # Vérification de la validité de la ligne
                if form.is_valid() == False or len(form.cleaned_data) == 0:
                    message = form.errors.as_data()["__all__"][0].message
                    raise forms.ValidationError("La ligne %d n'est pas valide : %s." % (index_ligne+1, message))

                # Vérifie que 2 lignes ne sont pas identiques sur les unités
                dict_ligne = form.cleaned_data
                if str(dict_ligne["unites"]) in liste_lignes_unites:
                    raise forms.ValidationError("Deux combinaisons d'unités semblent identiques")

                liste_lignes_unites.append(str(dict_ligne["unites"]))
                index_ligne += 1

        # Vérifie qu'au moins une ligne a été saisie
        if index_ligne == 0:
            raise forms.ValidationError("Vous devez saisir au moins une combinaison d'unités")


FORMSET_COMBI = inlineformset_factory(Aide, CombiAide, form=CombiAideForm, fk_name="aide", formset=BaseCombiAideFormSet,
                                            fields=["montant", "unites"], extra=0, min_num=1,
                                            can_delete=True, validate_max=True, can_order=False)



class Formulaire(FormulaireBase, ModelForm):
    montant_max = forms.DecimalField(label="Montant plafond", max_digits=6, decimal_places=2, initial=0.0, required=False)
    jours_scolaires = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_scolaires"))
    jours_vacances = forms.MultipleChoiceField(required=False, widget=forms.CheckboxSelectMultiple, choices=JOURS_SEMAINE, help_text=Creation_tout_cocher("jours_vacances"))
    individus = forms.ModelMultipleChoiceField(label="Bénéficiaires", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), queryset=Individu.objects.none(), required=True)

    class Meta:
        model = Aide
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille", None)
        idactivite = kwargs.pop("idactivite", None)
        idmodele = kwargs.pop("idmodele", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_aides_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Définit la famille associée
        if self.instance.pk:
            idfamille = self.instance.famille_id

        # Activité
        if self.instance.idaide != None:
            idactivite = self.instance.activite.idactivite

        self.fields["activite"].initial = Activite.objects.get(pk=idactivite).idactivite
        self.fields["activite"].disabled = True

        # Individus bénéficiaires
        individus = [rattachement.individu_id for rattachement in Rattachement.objects.filter(famille_id=idfamille)]
        self.fields['individus'].queryset = Individu.objects.filter(pk__in=individus).order_by("nom")

        # Jours
        self.fields["jours_scolaires"].initial = [0, 1, 2, 3, 4]
        self.fields["jours_vacances"].initial = [0, 1, 2, 3, 4]

        # Importation d'une aide
        if idmodele:
            modele_aide = Aide.objects.get(pk=idmodele)
            self.fields["nom"].initial = modele_aide.nom
            self.fields["caisse"].initial = modele_aide.caisse
            self.fields["date_debut"].initial = modele_aide.date_debut
            self.fields["date_fin"].initial = modele_aide.date_fin
            self.fields["jours_scolaires"].initial = modele_aide.jours_scolaires
            self.fields["jours_vacances"].initial = modele_aide.jours_vacances
            self.fields["montant_max"].initial = modele_aide.montant_max
            self.fields["nbre_dates_max"].initial = modele_aide.nbre_dates_max

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('famille', value=idfamille),
            Fieldset("Généralités",
                Field('activite'),
                Field('nom'),
                Field('caisse'),
                Field('date_debut'),
                Field('date_fin'),
            ),
            Fieldset("Bénéficiaires",
                Field("individus"),
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

    def clean(self):
        return self.cleaned_data


class Formulaire_selection_activite(FormulaireBase, forms.Form):
    activite = forms.ModelChoiceField(label="Activité", widget=Select_activite(), queryset=Activite.objects.all(), required=True)
    modele_aide = forms.ModelChoiceField(label="Modèle d'aide", widget=ModelSelect2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}, search_fields=['nom__icontains'], dependent_fields={"activite": "activite"}), queryset=Aide.objects.filter(famille__isnull=True), required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire_selection_activite, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Sélectionne uniquement les activités autorisées pour l'utilisateur
        self.fields["activite"].widget.attrs["request"] = self.request

        self.helper.layout = Layout(
            Field('activite'),
            Field('modele_aide'),
            ButtonHolder(
                Submit('submit', 'Valider', css_class='btn-primary'),
                HTML("""<a class="btn btn-danger" href="{{ view.Get_annuler_url }}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""),
                css_class="pull-right",
            )
        )
