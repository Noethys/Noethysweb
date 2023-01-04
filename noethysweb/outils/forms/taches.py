# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, HTML
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Tache, Structure
from core.widgets import DatePickerWidget


class Formulaire(FormulaireBase, ModelForm):
    acces = forms.ChoiceField(label="Utilisateurs associés", initial="automatique", required=True, help_text="Sélectionnez les utilisateurs concernés par cette tâche.", choices=[
        (None, "-------"), ("moi", "Uniquement moi"),
        ("structure", "Les utilisateurs de la structure suivante"),
        ("tous", "Tous les utilisateurs"),
    ])
    structure = forms.ModelChoiceField(label="Structure", queryset=Structure.objects.none(), required=False, help_text="Sélectionnez une structure dans la liste proposée.")

    class Meta:
        model = Tache
        fields = "__all__"
        widgets = {
            "titre": forms.Textarea(attrs={"rows": 4}),
            "date": DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'taches_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Focus
        self.fields["titre"].widget.attrs.update({'autofocus': 'autofocus'})

        # Date de parution
        if not self.instance.pk:
            self.fields["date"].initial = datetime.date.today()

        # Public
        self.fields["structure"].empty_label = "-------"
        if self.instance.pk:
            if self.instance.utilisateur:
                self.fields["acces"].initial = "moi"
            elif self.instance.structure:
                self.fields["acces"].initial = "structure"
            else:
                self.fields["acces"].initial = "tous"

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% if request.GET.next %}{{ request.GET.next }}{% else %}{% url 'taches_liste' %}{% endif %}"),
            HTML("<input type='hidden' name='next' value='{{ request.GET.next }}'>"),
            Fieldset("Tâche",
                Field("titre"),
                Field("date"),
            ),
            Fieldset("Public",
                Field("acces"),
                Field("structure"),
            ),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        # Public
        self.cleaned_data["utilisateur"] = self.request.user if self.cleaned_data["acces"] == "moi" else None
        self.cleaned_data["structure"] = self.cleaned_data["structure"] if self.cleaned_data["acces"] == "structure" else None
        if self.cleaned_data["acces"] == "structure" and not self.cleaned_data["structure"]:
            raise forms.ValidationError('Vous devez sélectionner une structure dans la liste proposée.')
        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_acces() {
        $('#div_id_structure').hide();
        if ($("#id_acces").val() == 'structure') {
            $('#div_id_structure').show();
        };
    }
    $(document).ready(function() {
        $('#id_acces').on('change', On_change_acces);
        On_change_acces.call($('#id_acces').get(0));
    });
</script>
"""
