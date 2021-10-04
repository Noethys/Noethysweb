# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, ButtonHolder, Fieldset, Div, Button
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.forms.base import FormulaireBase
import datetime


class Formulaire(FormulaireBase, forms.Form):
    nom = forms.CharField(label="Nom du fichier", help_text="Modifiez si besoin le nom du fichier de destination. L'extension nweb sera ajoutée automatiquement.", required=True)
    mdp1 = forms.CharField(label="Mot de passe", help_text="Saisissez un mot de passe qui servira au cryptage du fichier.", widget=forms.PasswordInput, required=True)
    mdp2 = forms.CharField(label="Confirmation", help_text="Confirmez le mot de passe en le saisissant une deuxième fois.", widget=forms.PasswordInput, required=True)
    inclure_media = forms.BooleanField(label="Inclure les images et documents dans la sauvegarde", required=False)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_sauvegarde_creer'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Nom de fichier initial
        nom_fichier = "Noethysweb_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M")
        self.fields["nom"].initial = nom_fichier

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'outils_toc' %}", enregistrer_label="<i class='fa fa-save margin-r-5'></i>Sauvegarder", ajouter=False),
            Field('nom'),
            Field('mdp1'),
            Field('mdp2'),
            Field('inclure_media'),
            # ButtonHolder(
            #     Div(
            #         Submit('bouton_submit', "Sauvegarder", css_class='btn-primary'),
            #         HTML("""<a class="btn btn-default" href="{% url 'outils_toc' %}">Annuler</a>"""),
            #         css_class="text-right"
            #     ),
            # ),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """
<div id="id_progress"></div>
<script>
$(document).ready(function() {
    $("#form_sauvegarde_creer").on('submit', function(event) {
        toastr.info("La création de la sauvegarde est lancée");
        $("#id_progress").html("<br><div class='callout callout-warning'><h4><i class='fa fa-refresh fa-spin margin-r-5'></i> <strong>Sauvegarde en cours.</strong></h4><p>Ne quittez pas cette page. Cette opération peut durer plusieurs minutes...</p></div>");
        //$('#form_sauvegarde_creer').submit();
    });
});  
</script>      
"""