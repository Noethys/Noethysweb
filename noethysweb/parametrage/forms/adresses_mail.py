# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import AdresseMail


class Formulaire(FormulaireBase, ModelForm):
    cle_api = forms.CharField(label="Clé API", required=False, help_text="Saisissez la clé API associée à votre compte.")
    cle_secrete = forms.CharField(label="Clé secrète", required=False, help_text="Saisissez la clé secrète associée à votre compte.")
    accuse = forms.BooleanField(label="Accusé de réception", required=False, initial=False, help_text="Compatible uniquement avec Microsoft Outlook.")
    motdepasse = forms.CharField(label="Mot de passe", widget=forms.TextInput(attrs={"type": "password"}), required=False, help_text="Saisissez le mot de passe associé à votre messagerie.")
    envoi_lot = forms.ChoiceField(label="Envoi par lot", choices=[("oui", "Activé"), ("non", "Désactivé")], initial="non", required=False, help_text="L'envoi par lot est recommandé si votre fournisseur de messagerie impose des limites d'envoi. Par exemple, Gmail permet d'envoyer uniquement 60 mails par minute.")
    nbre_mails = forms.IntegerField(label="Nombre de mails par lot", initial=50, min_value=0,required=False, help_text="Saisissez le nombre de mails à envoyer avant la pause.")
    duree_pause = forms.IntegerField(label="Durée de la pause (secondes)", initial=60, min_value=0, required=False, help_text="Saisissez le nombre de secondes de pause à appliquer entre chaque envoi de lot.")

    class Meta:
        model = AdresseMail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'adresses_mail_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Paramètres
        parametres = {}
        if self.instance:
            if self.instance.parametres:
                for parametre in self.instance.parametres.split("##"):
                    key, valeur = parametre.split("==")
                    parametres[key] = valeur

        if "notification" in parametres:
            self.fields['accuse'].initial = True
        if "api_key" in parametres:
            self.fields['cle_api'].initial = parametres["api_key"]
        if "api_secret" in parametres:
            self.fields['cle_secrete'].initial = parametres["api_secret"]
        if "nbre_mails" in parametres:
            self.fields['envoi_lot'].initial = "oui"
            self.fields['nbre_mails'].initial = int(parametres["nbre_mails"])
            self.fields['duree_pause'].initial = int(parametres["duree_pause"])

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'adresses_mail_liste' %}", autres_commandes=[
                HTML("""<a type='button' class='btn btn-default' data-toggle="modal" data-target="#modal_envoi_mail_test"><i class="fa fa-send-o margin-r-5"></i> Envoyer un Email de test</a> """),
            ]),
            Fieldset('Généralités',
                Field('moteur'),
                Field('actif'),
            ),
            Fieldset('Paramètres',
                Field('adresse'),
                Field('hote'),
                Field('port'),
                Field('utilisateur'),
                Field('motdepasse'),
                Field('nom_adresse'),
                Field('cle_api'),
                Field('cle_secrete'),
                Field('use_tls'),
                Field('accuse'),
                Field('envoi_lot'),
                Field('nbre_mails'),
                Field('duree_pause'),
            ),
            Fieldset("Options",
                Field("lien_desinscription"),
            ),
            # L'extrascript est placé à la fin pour ne pas perturber le bouton submit du form principal
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Vérification des données saisies
        if not self.cleaned_data.get("adresse", None):
            self.add_error('adresse', "Vous devez renseigner l'adresse d'expédition")
            return

        if self.cleaned_data["moteur"] == "smtp":

            if not self.cleaned_data["hote"]:
                self.add_error('hote', "Vous devez renseigner l'hôte")
                return

            if self.cleaned_data["envoi_lot"] == "oui" and not self.cleaned_data["nbre_mails"]:
                self.add_error('nbre_mails', "Vous devez renseigner le nombre de mails par lot")
                return

            if self.cleaned_data["envoi_lot"] == "oui" and not self.cleaned_data["duree_pause"]:
                self.add_error('duree_pause', "Vous devez renseigner la durée de la pause")
                return

        if self.cleaned_data["moteur"] == "mailjet":

            if not self.cleaned_data["cle_api"]:
                self.add_error('cle_api', "Vous devez renseigner la clé API")
                return

            if not self.cleaned_data["cle_secrete"]:
                self.add_error('cle_secrete', "Vous devez renseigner la clé secrète")
                return

        if self.cleaned_data["moteur"] == "brevo":

            if not self.cleaned_data["cle_api"]:
                self.add_error('cle_api', "Vous devez renseigner la clé API")
                return

        # Paramètres
        parametres = []

        if self.cleaned_data["moteur"] == "smtp" and self.cleaned_data["accuse"]:
            parametres.append("notification==1")

        if self.cleaned_data["moteur"] == "smtp" and self.cleaned_data["envoi_lot"] == "oui":
            parametres.append("nbre_mails==%d" % int(self.cleaned_data["nbre_mails"]))
            parametres.append("duree_pause==%d" % int(self.cleaned_data["duree_pause"]))

        if self.cleaned_data["moteur"] == "mailjet":
            parametres.append("api_key==%s" % self.cleaned_data["cle_api"])
            parametres.append("api_secret==%s" % self.cleaned_data["cle_secrete"])

        if self.cleaned_data["moteur"] == "brevo":
            parametres.append("api_key==%s" % self.cleaned_data["cle_api"])

        self.cleaned_data["parametres"] = "##".join(parametres)

        return self.cleaned_data



EXTRA_SCRIPT = """

{% load static %}
{% load embed %}

<script type="text/javascript" src="{% static 'lib/jquery-serialize-object/jquery.serialize-object.min.js' %}"></script>

<script>

// label_type
function On_change_moteur() {
    $('#div_id_adresse').hide();
    $('#div_id_nom_adresse').hide();
    $('#div_id_hote').hide();
    $('#div_id_port').hide();
    $('#div_id_utilisateur').hide();
    $('#div_id_motdepasse').hide();
    // $('#div_id_use_ssl').hide();
    $('#div_id_use_tls').hide();
    $('#div_id_cle_api').hide();
    $('#div_id_cle_secrete').hide();
    $('#div_id_accuse').hide();
    $('#div_id_envoi_lot').hide();
    $('#div_id_nbre_mails').hide();
    $('#div_id_duree_pause').hide();

    if($(this).val() == 'smtp') {
        $('#div_id_adresse').show();
        $('#div_id_nom_adresse').show();
        $('#div_id_hote').show();
        $('#div_id_port').show();
        $('#div_id_utilisateur').show();
        $('#div_id_motdepasse').show();
        // $('#div_id_use_ssl').show();
        $('#div_id_use_tls').show();
        $('#div_id_accuse').show();
        $('#div_id_envoi_lot').show();
        $("#id_envoi_lot").trigger("change");
    }
    
    if($(this).val() == 'mailjet') {
        $('#div_id_adresse').show();
        $('#div_id_nom_adresse').show();
        $('#div_id_cle_api').show();
        $('#div_id_cle_secrete').show();
    }

    if($(this).val() == 'brevo') {
        $('#div_id_adresse').show();
        $('#div_id_nom_adresse').show();
        $('#div_id_cle_api').show();
    }

    if($(this).val() == 'console') {
        $('#div_id_adresse').show();
    }

}
$(document).ready(function() {
    $('#id_moteur').change(On_change_moteur);
    On_change_moteur.call($('#id_moteur').get(0));
});

// envoi_lot
function On_change_envoi_lot() {
    $('#div_id_nbre_mails').hide();
    $('#div_id_duree_pause').hide();
    if ($(this).val() == 'oui') {
        $('#div_id_nbre_mails').show();
        $('#div_id_duree_pause').show();
    }
}
$(document).ready(function() {
    $('#id_envoi_lot').change(On_change_envoi_lot);
    On_change_envoi_lot.call($('#id_envoi_lot').get(0));
});

$(document).ready(function() {

    $('#modal_envoi_mail_test').on('show.bs.modal', function () {
        $('#modal_erreurs').html("");
        $("#adresse_destination").val($("#id_adresse").val());
    });

    $("#valider_envoi_mail_test").on('click', function(e) {
        $('#modal_erreurs').html("Veuillez patienter durant l'envoi...");
        $.ajax({
            type: "POST",
            url: "{% url 'ajax_envoyer_mail_test' %}",
            data: {
                form_adresse: JSON.stringify($("#adresses_mail_form").serializeObject()),
                adresse_destination: $("#adresse_destination").val(),
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


{# Modal Envoi Mail de test #}

{% embed 'core/modal.html' %}
    {% block modal_id %}modal_envoi_mail_test{% endblock %}
    {% block modal_titre %}Envoyer un Email de test{% endblock %}
    {% block modal_body %}
        <form id="form_envoi_mail_test" method="post">
            {% csrf_token %}
            <input type="hidden" id="saisie_memo_key" value="">
            <div>
                <div class="controls">
                    <label for="adresse_destination" class="col-form-label">Adresse de destination</label>
                    <input id="adresse_destination" class="form-control"></input>
                </div>
            </div>
            <div id="modal_erreurs" class="text-red" style="padding-top: 10px;"></div>
            <div class="buttonHolder">
                <div class="modal-footer" style="padding-bottom:0px;padding-right:0px;padding-left:0px;">
                    <button type="button" class="btn btn-primary" id="valider_envoi_mail_test"/>Envoyer</button>
                    <button type="button" class="btn btn-default" data-dismiss="modal">Fermer</button>
                </div>
            </div>
        </form>
    {% endblock %}
{% endembed %}


"""