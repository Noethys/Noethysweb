# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import ModelePlanningCollaborateur, TypeEvenementCollaborateur, LigneModelePlanningCollaborateur, JOURS_COMPLETS_SEMAINE
from parametrage.widgets import Ligne_modele_planning


class Formulaire(FormulaireBase, ModelForm):
    lignes = forms.CharField(label="Evènements", required=True, widget=Ligne_modele_planning(attrs={}))

    class Meta:
        model = ModelePlanningCollaborateur
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'modeles_plannings_collaborateurs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Lignes
        self.fields["lignes"].widget.request = self.request
        self.fields["lignes"].widget.attrs.update({
            "types_evenements": json.dumps({type_evenement.pk: type_evenement.nom for type_evenement in TypeEvenementCollaborateur.objects.all()}),
            "jours_semaine": json.dumps({num_jour: nom_jour for num_jour, nom_jour in JOURS_COMPLETS_SEMAINE}),
        })
        lignes = LigneModelePlanningCollaborateur.objects.select_related("type_evenement").filter(modele_id=self.instance.pk if self.instance else 0)
        self.fields["lignes"].initial = json.dumps([{
            "idligne": ligne.pk, "jour": ligne.jour, "periode": ligne.periode, "heure_debut": str(ligne.heure_debut),
            "heure_fin": str(ligne.heure_fin), "type_evenement": ligne.type_evenement_id, "titre": ligne.titre}
            for ligne in lignes])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_plannings_collaborateurs_liste' %}"),
            Fieldset("Généralités",
                Field("nom"),
                Field("observations"),
                Field("inclure_feries"),
            ),
            Fieldset("Evènements",
                Field("lignes"),
            ),
        )
