# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import UniteCotisation


class Formulaire(FormulaireBase, forms.Form):
    unite_cotisation = forms.ModelChoiceField(label="Unité d'adhésion", queryset=UniteCotisation.objects.none(), required=True,
        help_text="Sélectionnez l'unité d'adhésion pour laquelle vous souhaitez consulter la liste des adhérents.")

    def __init__(self, *args, **kwargs):
        kwargs.pop("instance", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"

        # Sélectionne uniquement les unités des types d'adhésion accessibles à l'utilisateur
        condition_structure = Q(type_cotisation__structure__in=self.request.user.structures.all()) | Q(type_cotisation__structure__isnull=True)
        self.fields["unite_cotisation"].queryset = UniteCotisation.objects.select_related("type_cotisation").filter(condition_structure).order_by("type_cotisation__nom", "nom")
        self.fields["unite_cotisation"].label_from_instance = lambda obj: "%s - %s" % (obj.type_cotisation.nom, obj.nom)

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Afficher la liste", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Field("unite_cotisation"),
        )
