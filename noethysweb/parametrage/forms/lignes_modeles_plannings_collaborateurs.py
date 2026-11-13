# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from crispy_forms.bootstrap import Field
from core.models import LigneModelePlanningCollaborateur, TypeEvenementCollaborateur
from collaborateurs.utils.utils_affectations import Arbre


class Formulaire(forms.ModelForm):
    idligne = forms.CharField(widget=forms.HiddenInput(), required=False)
    index = forms.CharField(widget=forms.HiddenInput(), required=False)
    nb_semaines = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    parite = forms.CharField(widget=forms.HiddenInput(), required=False)
    semaine = forms.TypedChoiceField(label="Semaine du cycle", required=False, coerce=int, empty_value=None, choices=[],
                                     help_text="Choisissez « Toutes les semaines du cycle » pour un créneau identique chaque semaine (par exemple pendant les vacances).")

    class Meta:
        model = LigneModelePlanningCollaborateur
        exclude = ["modele", "semaine"]
        widgets = {
            "heure_debut": forms.TimeInput(attrs={'type': 'time'}),
            "heure_fin": forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super(Formulaire, self).__init__(*args, **kwargs)

        # Semaine du cycle
        donnees = self.data or self.initial
        try:
            nb_semaines = max(1, int(donnees.get("nb_semaines") or 1))
        except (TypeError, ValueError):
            nb_semaines = 1
        parite = nb_semaines == 2 and str(donnees.get("parite")) in ("1", "true", "True")
        noms = {1: "Semaine impaire", 2: "Semaine paire"} if parite else {num: "Semaine %d" % num for num in range(1, nb_semaines + 1)}
        self.fields["semaine"].choices = [("", "Toutes les semaines du cycle")] + [(num, nom) for num, nom in noms.items()]
        if nb_semaines == 1:
            self.fields["semaine"].widget = forms.HiddenInput()
        self.helper = FormHelper()
        self.helper.form_id = "ligne_form"
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Type d'évènement
        types_evenements = TypeEvenementCollaborateur.objects.all().order_by("nom")
        self.fields["type_evenement"].choices = [(None, "---------")] + [(type_evenement.pk, type_evenement.nom) for type_evenement in types_evenements]
        self.fields["type_evenement"].required = True

        # Affectation
        self.fields["affectation"].choices = [(None, "---------")] + Arbre(actives_seulement=True).Get_choix()
        self.fields["affectation"].required = False

        self.helper.layout = Layout(
            Field("idligne"),
            Field("index"),
            Field("nb_semaines"),
            Field("parite"),
            Field("semaine"),
            Field("jour"),
            Field("periode"),
            Field("heure_debut"),
            Field("heure_fin"),
            Field("type_evenement"),
            Field("titre"),
            Field("affectation"),
        )
