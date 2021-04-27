# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm, ValidationError
from django.utils.translation import ugettext as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Row, Column, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, StrictButton
from core.utils.utils_commandes import Commandes
from core.models import Famille
from fiche_famille.widgets import Internet_identifiant, Internet_mdp


class Formulaire(ModelForm):
    internet_identifiant = forms.CharField(label="Identifiant", required=False, widget=Internet_identifiant())
    internet_mdp = forms.CharField(label="Mot de passe", required=False, widget=Internet_mdp())

    class Meta:
        model = Famille
        fields = ["internet_actif", "internet_identifiant", "internet_mdp"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_portail_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_resume' idfamille=idfamille %}", ajouter=False,
                      autres_commandes=[
                          HTML("""<a type='button' class='btn btn-default' title="Envoyer les codes par Email" onclick="impression_pdf()"><i class="fa fa-send-o margin-r-5"></i>Envoyer les codes par email</a> """)
                      ]),
            Hidden("idfamille", value=idfamille),
            Field("internet_actif"),
            Field("internet_identifiant"),
            Field("internet_mdp"),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        return self.cleaned_data


EXTRA_HTML = """

<script>

    function regenerer_identifiant() {
        $.ajax({
            type: "POST",
            url: "{% url 'ajax_regenerer_identifiant' %}",
            data: {
                idfamille: $('[name=idfamille]').val(),
                csrfmiddlewaretoken: "{{ csrf_token }}",
            },
            success: function (data) {
                $('#id_internet_identifiant').val(data.identifiant);
            },
            error: function (data) {
                toastr.error(data.responseJSON.erreur);
            }
        });
    };

    function regenerer_mdp() {
        $.ajax({
            type: "POST",
            url: "{% url 'ajax_regenerer_mdp' %}",
            data: {
                idfamille: $('[name=idfamille]').val(),
                csrfmiddlewaretoken: "{{ csrf_token }}",
            },
            success: function (data) {
                $('#id_internet_mdp').val(data.mdp);
                verrouillage_ctrl();
            },
            error: function (data) {
                toastr.error(data.responseJSON.erreur);
            }
        });
    };

</script>

<br>

"""