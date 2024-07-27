# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, ButtonHolder, Submit, HTML, Row, Column, Fieldset, Div
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
from core.widgets import DatePickerWidget
from core.models import Classe, NiveauScolaire
from core.forms.select2 import Select2MultipleWidget


class Formulaire(FormulaireBase, ModelForm):
    niveaux = forms.ModelMultipleChoiceField(label="Niveaux scolaires", widget=Select2MultipleWidget(), queryset=NiveauScolaire.objects.all(), required=False)

    class Meta:
        model = Classe
        fields = "__all__"
        widgets = {
            'date_debut': DatePickerWidget(),
            'date_fin': DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'classes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Récupération de l'école et des dates de la dernière classe saisie
        if self.instance.date_debut == None:
            classe = Classe.objects.last()
            if classe != None:
                self.fields["date_debut"].initial = classe.date_debut
                self.fields["date_fin"].initial = classe.date_fin
                self.fields["ecole"].initial = classe.ecole

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'classes_liste' %}"),
            Fieldset("Identification",
                Field('nom'),
                Field('ecole'),
            ),
            Fieldset("Saison",
                Field('date_debut'),
                Field('date_fin'),
            ),
            Fieldset('Niveaux scolaires',
                Field('niveaux'),
            ),
        )

    def clean_date_fin(self):
        if self.cleaned_data['date_debut'] > self.cleaned_data['date_fin'] :
            raise ValidationError("La date de fin doit être supérieure à la date de début.")
        return self.cleaned_data['date_fin']


class Formulaire_dupliquer(FormulaireBase, forms.Form):
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget())
    date_fin = forms.DateField(label="Date de fin", required=True, widget=DatePickerWidget())
    nom_ancien_texte = forms.CharField(label="Texte à remplacer dans le nom", required=False, help_text="[Optionnel] Saisissez le texte à remplacer dans le nom de la classe.")
    nom_nouveau_texte = forms.CharField(label="Remplacer par", required=False, help_text="[Optionnel] Saisissez le texte à insérer à la place du texte ci-dessus.")

    def __init__(self, *args, **kwargs):
        super(Formulaire_dupliquer, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'dupliquer_classes_form'
        self.helper.form_method = 'post'

        # Affichage
        self.helper.layout = Layout(
            Commandes(enregistrer=False, ajouter=False, annuler=False, aide=False, autres_commandes=[
                HTML("""<button type="button" onclick="valider_form_dupliquer()" title="Valider" class="btn btn-primary"><i class="fa fa-check margin-r-5"></i>Valider</button> """),
                HTML("""<a class="btn btn-danger" title="Annuler" onclick="$('#modal_dupliquer').modal('hide');"><i class="fa fa-ban margin-r-5"></i>Annuler</a> """),
            ],),
            Field("date_debut"),
            Field("date_fin"),
            Field("nom_ancien_texte"),
            Field("nom_nouveau_texte"),
        )

    def clean_date_fin(self):
        if self.cleaned_data['date_debut'] > self.cleaned_data['date_fin'] :
            raise ValidationError("La date de fin doit être supérieure à la date de début.")
        return self.cleaned_data['date_fin']
