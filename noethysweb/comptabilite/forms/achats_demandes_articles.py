# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.models import AchatArticle, AchatCategorie, AchatFournisseur
from core.widgets import Select_avec_commandes_advanced
from core.utils import utils_parametres


class Formulaire(forms.ModelForm):
    idarticle = forms.CharField(widget=forms.HiddenInput(), required=False)
    index = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = AchatArticle
        exclude = ["demande",]
        widgets = {
            "fournisseur": Select_avec_commandes_advanced(attrs={"id_form": "achats_fournisseurs_form", "module_form": "parametrage.forms.achats_fournisseurs", "nom_objet": "un fournisseur", "champ_nom": "nom"}),
            "categorie": Select_avec_commandes_advanced(attrs={"id_form": "achats_categories_form", "module_form": "parametrage.forms.achats_categories", "nom_objet": "une catégorie", "champ_nom": "nom"}),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "fournisseur": "Sélectionnez un fournisseur dans la liste. S'il n'existe pas, cliquez sur le bouton +.",
            "categorie": "Sélectionnez une catégorie d'articles dans la liste. Si elle n'existe pas, cliquez sur le bouton +.",
            "libelle": "Saisissez un libellé pour cet article. Exemples : Farine, Baguette de pain, Ballon, Thé, etc...",
            "quantite": "Saisissez la quantité à acheter en précisant l'unité de mesure si besoin. Exemples : 1, 8, 2 Kg, 300g, 1 par individu, etc...",
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "article_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Fournisseur
        self.fields["fournisseur"].queryset = AchatFournisseur.objects.filter(Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")
        if not self.instance.pk:
            fournisseur_defaut = utils_parametres.Get(utilisateur=request.user, nom="fournisseur", categorie="achats_demandes_articles", valeur=None)
            if fournisseur_defaut:
                self.fields["fournisseur"].initial = fournisseur_defaut

        # Catégorie
        categories = AchatCategorie.objects.filter((Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True))).order_by("nom")
        self.fields["categorie"].choices = [(None, "---------")] + [(categorie.pk, categorie.nom) for categorie in categories]
        if not self.instance.pk:
            categorie_defaut = utils_parametres.Get(utilisateur=request.user, nom="categorie", categorie="achats_demandes_articles", valeur=None)
            if categorie_defaut:
                self.fields["categorie"].initial = categorie_defaut

        self.helper.layout = Layout(
            Field("idarticle"),
            Field("index"),
            Field("fournisseur"),
            Field("categorie"),
            Field("libelle"),
            Field("quantite"),
            Field("observations"),
            Field("achete"),
        )

    def clean(self):
        if not self.cleaned_data["libelle"]:
            self.add_error("libelle", "Vous devez saisir un libellé.")
            return
        return self.cleaned_data
