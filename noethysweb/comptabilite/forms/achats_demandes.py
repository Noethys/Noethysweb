# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.select2 import Select2Widget
from core.forms.base import FormulaireBase
from core.widgets import DatePickerWidget
from core.utils.utils_commandes import Commandes
from core.models import AchatDemande, AchatCategorie, AchatArticle, AchatFournisseur, Collaborateur
from comptabilite.widgets import Achats_demandes_articles


class Formulaire(FormulaireBase, ModelForm):
    collaborateur = forms.ModelChoiceField(label="Collaborateur", widget=Select2Widget({"data-minimum-input-length": 0}),
                                            queryset=Collaborateur.objects.all().order_by("nom", "prenom"), required=False, help_text="Sélectionnez le collaborateur à l'origine de la demande.")
    articles = forms.CharField(label="Articles", required=False, widget=Achats_demandes_articles(attrs={}))

    class Meta:
        model = AchatDemande
        fields = "__all__"
        widgets = {
            "date_echeance": DatePickerWidget(),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "date_echeance": "Saisissez la date pour laquelle cet achat doit être effectué.",
            "libelle": "Saisissez l'intitulé de la demande. Il peut s'agir par exemple d'un motif ou d'une utilisation.",
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "achats_demandes_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Articles
        self.fields["articles"].widget.request = self.request
        self.fields["articles"].widget.attrs.update({
            "fournisseurs": json.dumps({fournisseur.pk: fournisseur.nom for fournisseur in AchatFournisseur.objects.all()}),
            "categories": json.dumps({categorie.pk: categorie.nom for categorie in AchatCategorie.objects.all()}),
        })
        articles = AchatArticle.objects.select_related("fournisseur", "categorie").filter(demande=self.instance if self.instance else 0)
        self.fields["articles"].initial = json.dumps([{"idarticle": a.pk, "fournisseur": a.fournisseur_id, "categorie": a.categorie_id, "libelle": a.libelle,
                                                       "quantite": a.quantite, "observations": a.observations, "achete": a.achete} for a in articles])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'achats_demandes_liste' %}"),
            Fieldset("Généralités",
                Field("date_echeance"),
                Field("collaborateur"),
                Field("libelle"),
            ),
            Fieldset("Articles",
                Field("articles"),
            ),
            Fieldset("Options",
                Field("observations"),
            ),
        )
