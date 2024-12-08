# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import NomTarif, Activite


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = NomTarif
        fields = "__all__"
        help_texts = {
            "nom": "Vous devez saisir un nom de tarif. Exemples : Journée avec repas, Atelier, Séjour à la neige - Février 2026, Yoga - Saison 2024-25...",
        }

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_noms_tarifs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        if hasattr(self.instance, "activite") == False:
            activite = Activite.objects.get(pk=idactivite)
        else:
            activite = self.instance.activite

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=activite.idactivite),
            Field("nom"),
        )
