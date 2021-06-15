# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, ButtonHolder, Fieldset, Div, Button
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.widgets import Selection_fichier
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, forms.Form):
    fichier = forms.FileField(label="Fichier à restaurer", help_text="Sélectionnez le fichier de sauvegarde à restaurer (Avec extension .nweb).", required=True, widget=Selection_fichier(attrs={"accept": ".nweb"}))
    mdp = forms.CharField(label="Mot de passe", help_text="Saisissez le mot de passe utilisé pour crypter la sauvegarde.", widget=forms.PasswordInput, required=True)
    confirmation1 = forms.BooleanField(label="J'ai bien noté que cette opération de restauration peut durer plusieurs heures", required=True)
    confirmation2 = forms.BooleanField(label="Je confirme vouloir écraser la base de données existante", required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form_sauvegarde_restaurer'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.use_custom_control = False

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'outils_toc' %}", enregistrer_label="<i class='fa fa-upload margin-r-5'></i>Restaurer", ajouter=False),
            Field('fichier'),
            Field('mdp'),
            Field('confirmation1'),
            Field('confirmation2'),
            # ButtonHolder(
            #     Div(
            #         Submit('bouton_submit', _("Restaurer"), css_class='btn-primary'),
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
    $("#form_sauvegarde_restaurer").on('submit', function(event) {
        toastr.info("La restauration est lancée");
        $("#id_progress").html("<br><div class='alert alert-warning alert-dismissible'><h4><i class='fa fa-refresh fa-spin margin-r-5'></i> <strong>Restauration en cours.</strong></h4><p>Ne quittez pas cette page. Cette opération peut durer plusieurs heures...</p></div>");
        //$('#form_sauvegarde_restaurer').submit();
    });
});  
</script>      
"""