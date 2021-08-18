# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from core.models import Famille, PortailRenseignement, Rattachement
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = Famille
        fields = ["caisse", "num_allocataire", "allocataire", "autorisation_cafpro"]
        labels = {
            "caisse": "Caisse d'allocation",
            "autorisation_cafpro": "Autorise l'administrateur à récupérer le quotient familial auprès de la CAF",
        }

    def __init__(self, *args, **kwargs):
        self.famille = kwargs.pop('famille', None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "famille_caisse"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_caisse_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Allocataire
        rattachements = Rattachement.objects.select_related('individu').filter(famille=self.famille).order_by("individu__nom", "individu__prenom")
        self.fields["allocataire"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]

        # Help_texts pour le mode édition
        self.help_texts = {
            "caisse": "Sélectionnez une caisse d'allocation dans la liste déroulante.",
            "num_allocataire": "Saisissez le numéro d'allocataire.",
            "allocataire": "Sélectionnez le titulaire du dossier auprès de la caisse d'allocation.",
            "autorisation_cafpro": "Cochez la case pour autoriser la récupération du quotient familial auprès de la CAF par l'administrateur. Uniquement pour les familles allocataires de la CAF.",
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": "Caisse", "champs": ["caisse", "num_allocataire", "allocataire", "autorisation_cafpro"]},
        ]

        # Préparation du layout
        self.Set_layout()
