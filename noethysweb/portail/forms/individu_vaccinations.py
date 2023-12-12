# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset
from crispy_forms.bootstrap import Field
from core.models import Vaccin, TypeVaccin
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = Vaccin
        fields = "__all__"
        widgets = {
            'date': DatePickerWidget(),
        }
        help_texts = {
            "type_vaccin": _("Sélectionnez le type de vaccination dans la liste."),
            "date": _("Saisissez la date de la vaccination."),
        }

    def __init__(self, *args, **kwargs):
        rattachement = kwargs.pop("rattachement", None)
        mode = kwargs.pop("mode", "MODIFICATION")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_vaccinations_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # self.helper.use_custom_control = False

        # Tri des types de vaccins par ordre alpha
        self.fields["type_vaccin"].queryset = TypeVaccin.objects.all().order_by("nom")

        # Affichage
        self.helper.layout = Layout(
            Hidden('individu', value=rattachement.individu_id),
            Fieldset("Vaccination",
                Field("type_vaccin"),
                Field("date"),
            ),
            Commandes(annuler_url="{% url 'portail_individu_vaccinations' idrattachement=rattachement.pk %}", aide=False, ajouter=False, css_class="pull-right"),
        )
