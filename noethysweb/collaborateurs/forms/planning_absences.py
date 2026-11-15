# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.forms.select2 import Select2MultipleWidget
from core.models import GroupeCollaborateurs, TypeEvenementCollaborateur
from collaborateurs.utils import utils_absences

NOMS_MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def Get_choix_mois(nbre_avant=24, nbre_apres=18):
    """ Liste des mois proposés : ("AAAA-MM", "Novembre 2026") """
    aujourdhui = datetime.date.today()
    index = aujourdhui.year * 12 + aujourdhui.month - 1
    return [("%04d-%02d" % (n // 12, n % 12 + 1), "%s %d" % (NOMS_MOIS[n % 12], n // 12)) for n in range(index - nbre_avant, index + nbre_apres + 1)]


def Lire_mois(texte=""):
    """ "2026-11" -> date du premier jour du mois """
    annee, mois = texte.split("-")
    return datetime.date(int(annee), int(mois), 1)


class Formulaire(FormulaireBase, forms.Form):
    mois = forms.ChoiceField(label="Premier mois affiché", choices=[], required=True)
    nbre_mois = forms.TypedChoiceField(label="Nombre de mois", choices=[(1, "1 mois"), (2, "2 mois"), (3, "3 mois")], coerce=int, initial=1, required=True)
    groupes = forms.ModelMultipleChoiceField(label="Groupes de collaborateurs", queryset=GroupeCollaborateurs.objects.all().order_by("nom"), required=False,
                                             widget=Select2MultipleWidget({"data-minimum-input-length": 0}), help_text="Laissez vide pour tous les collaborateurs.")
    regrouper = forms.BooleanField(label="Regrouper par groupe de collaborateurs", required=False, initial=True,
                                   help_text="Affiche le nombre d'absents de chaque groupe, jour par jour.")
    situation = forms.ChoiceField(label="Collaborateurs", required=True, initial="en_poste",
                                  choices=[("en_poste", "Sous contrat pendant la période"), ("tous", "Tous les collaborateurs")])
    categories = forms.ModelMultipleChoiceField(label="Catégories d'absences", queryset=TypeEvenementCollaborateur.objects.none(), widget=forms.CheckboxSelectMultiple, required=True)
    afficher_attente = forms.BooleanField(label="Afficher les demandes en attente", required=False, initial=True,
                                          help_text="Les demandes d'absence non encore validées sont hachurées.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "form_parametres"
        self.helper.form_method = "post"

        self.fields["mois"].choices = Get_choix_mois()
        self.fields["mois"].initial = datetime.date.today().strftime("%Y-%m")
        categories = utils_absences.Get_categories_absence()
        self.fields["categories"].queryset = TypeEvenementCollaborateur.objects.filter(pk__in=categories.keys()).order_by("nom")
        self.fields["categories"].initial = list(categories.keys())

        self.helper.layout = Layout(
            Field("mois"),
            Field("nbre_mois"),
            Field("groupes"),
            Field("regrouper"),
            Field("situation"),
            Field("categories"),
            Field("afficher_attente"),
        )
