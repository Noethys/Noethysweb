# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Max
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import TransportArret


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = TransportArret
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        categorie = kwargs.pop("categorie", None)
        idligne = kwargs.pop("idligne")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "arrets_form"
        self.helper.form_method = "post"

        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-md-2"
        self.helper.field_class = "col-md-10"

        # Ordre
        if self.instance.ordre == None:
            max = TransportArret.objects.filter(ligne_id=idligne).aggregate(Max('ordre'))['ordre__max']
            if max == None:
                max = 0
            self.fields['ordre'].initial = max + 1
        else:
            self.fields['ordre'].initial = self.instance.ordre

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'arrets_liste' categorie=categorie idligne=idligne %}"),
            Hidden("categorie", value=categorie),
            Hidden("ligne", value=idligne),
            Hidden('ordre', value=self.fields['ordre'].initial),
            Fieldset("Identification",
                Field("nom"),
            ),
        )
