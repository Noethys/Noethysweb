# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, ButtonHolder
from crispy_forms.bootstrap import Field, FormActions, PrependedText, StrictButton
from core.utils.utils_commandes import Commandes
import datetime
from core.forms.select2 import Select2MultipleWidget
from core.models import TypeGroupeActivite, Activite


class ChampActivites(forms.ModelMultipleChoiceField):
    def label_from_instance(self, activite):
        # Signale les activités terminées pour les distinguer des activités homonymes en cours
        if activite.date_fin and activite.date_fin < datetime.date.today():
            return "%s (terminée le %s)" % (activite.nom, activite.date_fin.strftime("%d/%m/%Y"))
        return activite.nom


class Formulaire(FormulaireBase, ModelForm):
    activites = ChampActivites(label="Activités", widget=Select2MultipleWidget(), queryset=Activite.objects.none(), required=False,
                               help_text="Sélectionnez les activités qui appartiennent à ce groupe. Une activité peut appartenir à plusieurs groupes. "
                                         "Cette sélection est synchronisée avec le champ Groupes d'activités de la fiche de chaque activité. "
                                         "Seules les activités de vos structures sont proposées.")

    class Meta:
        model = TypeGroupeActivite
        fields = "__all__"
        help_texts = {
            "nom": "Saisissez un nom qui décrit l'ensemble des activités regroupées. Exemples : Périscolaire, Extrascolaire, Vacances, Sport et culture... "
                   "Ce groupe permettra ensuite de sélectionner toutes ses activités en une seule fois dans les états, listes, statistiques et générations de factures.",
            "structure": "Sélectionnez la structure associée à ce groupe d'activités.",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'types_groupes_activites_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Activités associées : uniquement celles des structures de l'utilisateur
        if self.request:
            self.fields["activites"].queryset = Activite.objects.filter(structure__in=self.request.user.structures.all()).order_by("nom", "date_debut")
        if self.instance.pk:
            self.fields["activites"].initial = self.instance.activite_groupes_activites.filter(pk__in=self.fields["activites"].queryset)

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'types_groupes_activites_liste' %}"),
            Field('nom'),
            Field("structure"),
            Field("activites"),
        )

    def save(self, commit=True):
        instance = super(Formulaire, self).save(commit=commit)
        if commit:
            self.Enregistrer_activites(instance)
        else:
            save_m2m = self.save_m2m
            def save_m2m_activites():
                save_m2m()
                self.Enregistrer_activites(instance)
            self.save_m2m = save_m2m_activites
        return instance

    def Enregistrer_activites(self, instance):
        """ Ajoute ou retire le groupe sur les activités sans toucher aux activités des autres structures """
        selection = set(self.cleaned_data["activites"])
        visibles = set(self.fields["activites"].queryset)
        actuelles = set(instance.activite_groupes_activites.all())
        instance.activite_groupes_activites.remove(*((actuelles & visibles) - selection))
        instance.activite_groupes_activites.add(*(selection - actuelles))
