# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.models import Structure


class Formulaire(FormulaireBase, forms.Form):
    profil_nom = forms.CharField(label="Nom", required=False, help_text="Saisissez un titre pour ce profil. Ex : 'Ma liste préférée', 'Liste spéciale cantine'...")
    profil_utilisateurs = forms.ChoiceField(label="Utilisateurs associés", initial="automatique", required=False, help_text="Sélectionnez les utilisateurs qui auront accès à ce profil.", choices=[
        ("moi", "Uniquement moi"),
        ("structure", "Les utilisateurs de la structure suivante"),
        ("tous", "Tous les utilisateurs"),
    ])
    profil_structure = forms.ModelChoiceField(label="Structure", queryset=Structure.objects.none(), required=False, help_text="Sélectionnez une structure dans la liste proposée.")

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_profil_configuration'
        self.helper.form_method = 'post'
        self.helper.form_tag = False
        self.helper.disable_csrf = True

        # Importe uniquement les structures de l'utilisateur en cours
        self.fields["profil_structure"].queryset = self.request.user.structures.all().order_by("nom")

        self.helper.layout = Layout(
            Field('profil_nom'),
            Field('profil_utilisateurs'),
            Field('profil_structure'),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<script>
    function On_change_utilisateurs() {
        $('#div_id_profil_structure').hide();
        if ($("#id_profil_utilisateurs").val() == 'structure') {
            $('#div_id_profil_structure').show();
        };
    }
    $(document).ready(function() {
        $('#id_profil_utilisateurs').on('change', On_change_utilisateurs);
        On_change_utilisateurs.call($('#id_profil_utilisateurs').get(0));
    });
</script>
"""
