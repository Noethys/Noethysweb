# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Consommation, Groupe, Unite, CategorieTarif, Prestation, Evenement
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    prestation = forms.IntegerField(label="ID Prestation", required=False)
    evenement = forms.IntegerField(label="ID Evénement", required=False)
    heure_debut = forms.TimeField(label="Heure de début", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))
    heure_fin = forms.TimeField(label="Heure de fin", required=False, widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = Consommation
        fields = ["date", "unite", "groupe", "etat", "quantite", "evenement", "heure_debut", "heure_fin", "categorie_tarif", "prestation"]
        widgets = {
            "date": DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'liste_consommations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Unités de consommation
        self.fields["unite"].choices = [(unite.pk, unite.nom) for unite in Unite.objects.filter(activite_id=self.instance.activite_id).order_by("nom")]

        # Groupes
        self.fields["groupe"].choices = [(groupe.pk, groupe.nom) for groupe in Groupe.objects.filter(activite_id=self.instance.activite_id).order_by("ordre")]

        # Catégories de tarifs
        self.fields["categorie_tarif"].choices = [(categorie.pk, categorie.nom) for categorie in CategorieTarif.objects.filter(activite_id=self.instance.activite_id).order_by("nom")]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'liste_consommations' %}", ajouter=False),
            Div(
                HTML("<i class='fa fa-warning'></i> Attention, la modification des paramètres ci-dessous n'implique aucune vérification de cohérence et n'entraîne aucun recalcul de la prestation associée. Ne modifiez donc ces paramètres qu'en connaissance de cause sous peine de générer des erreurs statistiques ou de facturation."),
                css_class="alert alert-warning"
            ),
            Fieldset("Généralités",
                Field("date"),
                Field("unite"),
                Field("groupe"),
                Field("etat"),
                Field("quantite"),
                Field("evenement"),
            ),
            Fieldset("Horaires",
                Field("heure_debut"),
                Field("heure_fin"),
            ),
            Fieldset("Tarification",
                Field("categorie_tarif"),
                Field("prestation"),
            ),
        )
        self.helper.layout.insert(2,
            Div(HTML("""
                <span>Individu : %s</span>
                <span class="ml-5">Activité : %s</span>
                <span class="ml-5">Famille : %s</span>
                """ % (self.instance.individu, self.instance.activite, self.instance.inscription.famille)),
                css_class="alert alert-light text-center"
            ),
        )

    def clean(self):
        if not self.cleaned_data["etat"]:
            self.add_error("etat", "Vous devez sélectionner un état dans la liste proposée.")
            return

        if self.cleaned_data["evenement"]:
            self.cleaned_data["evenement"] = Evenement.objects.get(pk=self.cleaned_data["evenement"])

        if self.cleaned_data["prestation"]:
            self.cleaned_data["prestation"] = Prestation.objects.get(pk=self.cleaned_data["prestation"])

        return self.cleaned_data
