# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from core.models import Individu, Medecin
from portail.forms.fiche import FormulaireBase
from core.widgets import Select_avec_commandes_form


class Form_choix_medecin(forms.ModelChoiceField):
    search_fields = ['nom__icontains', 'prenom__icontains', 'ville_resid__icontains']

    def label_from_instance(self, instance):
        return instance.Get_nom(afficher_ville=True)


class Formulaire(FormulaireBase, ModelForm):
    medecin = Form_choix_medecin(label=_("Médecin"), queryset=Medecin.objects.all().order_by("nom", "prenom"), required=False,
                                     widget=Select_avec_commandes_form(attrs={"url_ajax": "portail_ajax_ajouter_medecin", "id_form": "medecins_form", "afficher_bouton_ajouter": False,
                                                                              "textes": {"champ": "Nom du médecin", "ajouter": "Ajouter un médecin", "modifier": "Modifier un médecin"}}))

    class Meta:
        model = Individu
        fields = ["medecin"]

    def __init__(self, *args, **kwargs):
        self.rattachement = kwargs.pop("rattachement", None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "individu_medecin"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_medecin_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Help_texts pour le mode édition
        self.help_texts = {
            "medecin": _("Cliquez sur le champ ci-dessus pour sélectionner un médecin dans la liste déroulante. Vous pouvez faire une recherche par nom, par prénom ou par ville") + ". <a href='#' class='ajouter_element'>" + _("Cliquez ici pour ajouter un médecin manquant dans la liste de choix") + ".</a>",
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": _("Médecin traitant"), "champs": ["medecin"]},
        ]

        # Préparation du layout
        self.Set_layout()
