# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import PortailDocument, TypePiece
from core.utils.utils_commandes import Commandes


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = PortailDocument
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_documents_form'
        self.helper.form_method = 'post'
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Sélectionne uniquement les activités autorisées
        self.fields["type_piece"].queryset = TypePiece.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'portail_documents_liste' %}"),
            Fieldset("Généralités",
                Field("titre"),
                Field("texte"),
                Field("couleur_fond"),
            ),
            Fieldset("Document joint",
                Field("document"),
            ),
            Fieldset("Type de pièce associé",
                Field("type_piece"),
            ),
            Fieldset("Structure associée",
                Field("structure"),
            ),
        )
