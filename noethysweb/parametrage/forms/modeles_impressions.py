# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import importlib, json
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import ModeleImpression, ModeleDocument
from core.widgets import FormIntegreWidget


class Formulaire(FormulaireBase, ModelForm):
    options = forms.CharField(label="Options d'impression", required=False, widget=FormIntegreWidget())

    class Meta:
        model = ModeleImpression
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        categorie = kwargs.pop("categorie")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_impressions_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Modèle de document
        self.fields["modele_document"].queryset = ModeleDocument.objects.filter(categorie=categorie).order_by("nom")
        self.fields["modele_document"].required = True

        # Options
        if categorie == "facture":
            nom_module = "facturation.forms.factures_options_impression"
        if categorie == "attestation_fiscale":
            nom_module = "facturation.forms.attestations_fiscales_options_impression"
        if categorie == "attestation_presence":
            nom_module = "facturation.forms.attestations_options_impression"
        if categorie == "devis":
            nom_module = "facturation.forms.devis_options_impression"
        if categorie == "rappel":
            nom_module = "facturation.forms.rappels_options_impression"
        if categorie == "reglement":
            nom_module = "parametrage.forms.modele_impression_recu"

        module = importlib.import_module(nom_module)
        self.form_options = getattr(module, "Formulaire")
        initial_data_options = json.loads(self.instance.options) if self.instance.options else None
        self.fields["options"].widget.attrs.update({"hauteur": 300, "form": self.form_options(request=self.request, initial=initial_data_options, memorisation=False)})

        # Définir comme valeur par défaut
        self.fields['defaut'].label = "Définir comme modèle par défaut"
        if len(ModeleImpression.objects.filter(categorie=categorie)) == 0 or self.instance.defaut == True:
            self.fields['defaut'].initial = True
            # self.fields['defaut'].disabled = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('categorie', value=categorie),
            Fieldset("Généralités",
                Field("nom"),
                Field("description"),
                Field("structure"),
                Field("defaut"),
            ),
            Fieldset("Modèle de document",
                Field("modele_document"),
            ),
            Fieldset("Options",
                Field("options"),
            ),
        )

    def clean(self):
        # Vérification du formulaire des options d'impression
        form_options = self.form_options(self.data, request=self.request)
        if not form_options.is_valid():
            liste_erreurs = form_options.errors.as_data().keys()
            self.add_error("options", "Veuillez renseigner les champs manquants : %s." % ", ".join(liste_erreurs))

        # Rajoute les options d'impression formatées aux résultats du formulaire
        self.cleaned_data["options"] = form_options.cleaned_data
        return self.cleaned_data
