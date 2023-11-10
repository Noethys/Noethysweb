# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import ModelForm, TextInput
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import ConfigurationSMS


class Formulaire(FormulaireBase, ModelForm):
    class Meta:
        model = ConfigurationSMS
        fields = "__all__"
        widgets = {
            "motdepasse": TextInput(attrs={"type": "password"})
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'configurations_sms_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'configurations_sms_liste' %}", autres_commandes=[
                HTML("""<a type='button' class='btn btn-default' data-toggle="modal" data-target="#modal_envoi_sms_test"><i class="fa fa-send-o margin-r-5"></i> Envoyer un SMS de test</a> """),
            ]),
            Fieldset('Généralités',
                Field('moteur'),
            ),
            Fieldset('Paramètres',
                Field('token'),
                Field('nom_exp'),
                Field('nom_compte'),
                Field('identifiant'),
                Field('motdepasse'),
            ),
            Fieldset('Options',
                Field('nbre_caracteres'),
                Field('montant_unitaire'),
                Field('solde'),
            ),
            # L'extrascript est placé à la fin pour ne pas perturber le bouton submit du form principal
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):

        if self.cleaned_data["moteur"] == "mailjet":
            if not self.cleaned_data["token"]:
                self.add_error("token", "Vous devez renseigner le token communiqué par le fournisseur")
                return
            if not self.cleaned_data["nom_exp"]:
                self.add_error("nom_exp", "Vous devez renseigner un nom d'expéditeur")
                return

        if self.cleaned_data["moteur"] == "ovh":
            if not self.cleaned_data["nom_compte"]:
                self.add_error("nom_compte", "Vous devez renseigner le nom du compte")
                return
            if not self.cleaned_data["identifiant"]:
                self.add_error("identifiant", "Vous devez renseigner l'identifiant")
                return
            if not self.cleaned_data["motdepasse"]:
                self.add_error("motdepasse", "Vous devez renseigner le mot de passe")
                return

        if self.cleaned_data["moteur"] == "brevo":
            if not self.cleaned_data["token"]:
                self.add_error("token", "Vous devez renseigner le token communiqué par le fournisseur")
                return
            if not self.cleaned_data["nom_exp"]:
                self.add_error("nom_exp", "Vous devez renseigner un nom d'expéditeur")
                return

        return self.cleaned_data



EXTRA_SCRIPT = """

{% load static %}
{% load embed %}

<script type="text/javascript" src="{% static 'lib/jquery-serialize-object/jquery.serialize-object.min.js' %}"></script>

<script>

// label_type
function On_change_moteur() {
    $('#div_id_token').hide();
    $('#div_id_nom_exp').hide();
    $('#div_id_nom_compte').hide();
    $('#div_id_identifiant').hide();
    $('#div_id_motdepasse').hide();

    if ($(this).val() == 'mailjet') {
        $('#div_id_token').show();
        $('#div_id_nom_exp').show();
    }
    
    if ($(this).val() == 'ovh') {
        $('#div_id_nom_exp').show();
        $('#div_id_nom_compte').show();
        $('#div_id_identifiant').show();
        $('#div_id_motdepasse').show();
    }

    if ($(this).val() == 'brevo') {
        $('#div_id_token').show();
        $('#div_id_nom_exp').show();
    }
    
}
$(document).ready(function() {
    $('#id_moteur').change(On_change_moteur);
    On_change_moteur.call($('#id_moteur').get(0));
});

$(document).ready(function() {

    $('#modal_envoi_sms_test').on('show.bs.modal', function () {
        $('#modal_erreurs').html("");
    });

    $("#valider_envoi_sms_test").on('click', function(e) {
        $('#modal_erreurs').html("Veuillez patienter durant l'envoi...");
        $.ajax({
            type: "POST",
            url: "{% url 'ajax_envoyer_sms_test' %}",
            data: {
                configuration: JSON.stringify($("#configurations_sms_form").serializeObject()),
                numero_destination: $("#numero_destination").val(),
                csrfmiddlewaretoken: '{{ csrf_token }}',
            },
            datatype: "json",
            success: function(data){
                $('#modal_erreurs').html(data.resultat);
            },
            error: function(data) {
                $('#modal_erreurs').html(data.responseJSON.erreur);
            }
        });
    });

});

</script>


{# Modal Envoi SMS de test #}

{% embed 'core/modal.html' %}
    {% block modal_id %}modal_envoi_sms_test{% endblock %}
    {% block modal_titre %}Envoyer un SMS de test{% endblock %}
    {% block modal_body %}
        <form id="form_envoi_sms_test" method="post">
            {% csrf_token %}
            <input type="hidden" id="saisie_memo_key" value="">
            <div>
                <div class="controls">
                    <label for="numero_destination" class="col-form-label">Numéro de destination</label>
                    <input id="numero_destination" class="form-control"></input>
                </div>
            </div>
            <div id="modal_erreurs" class="text-red" style="padding-top: 10px;"></div>
            <div class="buttonHolder">
                <div class="modal-footer" style="padding-bottom:0px;padding-right:0px;padding-left:0px;">
                    <button type="button" class="btn btn-primary" id="valider_envoi_sms_test"/>Envoyer</button>
                    <button type="button" class="btn btn-default" data-dismiss="modal">Fermer</button>
                </div>
            </div>
        </form>
    {% endblock %}
{% endembed %}

"""
