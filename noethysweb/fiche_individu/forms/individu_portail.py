# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset
from crispy_forms.bootstrap import Field
from django_select2.forms import Select2MultipleWidget
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Famille, Individu, Rattachement
from fiche_individu.widgets import Internet_identifiant, Internet_mdp


class Formulaire(FormulaireBase, ModelForm):
    internet_identifiant = forms.CharField(label="Identifiant", required=False, widget=Internet_identifiant(), help_text="Cet identifiant est généré automatiquement, il est conseillé de ne pas le modifier.")
    internet_mdp = forms.CharField(label="Mot de passe", required=False, widget=Internet_mdp(), help_text="Des étoiles ***** apparaissent lorsque le mot de passe a été personnalisé par l'utilisateur lors de la première connexion au portail. Dans ce cas, il vous est impossible de récupérer le mot de passe personnalisé, vous devez en générer un nouveau.")
    date_expiration_mdp = forms.DateTimeField(label="Date d'expiration", required=False)
    individus_masques = forms.ModelMultipleChoiceField(label="Individus masqués", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), queryset=Individu.objects.none(), required=False, help_text="Vous pouvez sélectionner des membres de la individu qui n'apparaitront pas sur le portail.")

    class Meta:
        model = Individu
        fields = ["internet_actif", "internet_identifiant", "internet_mdp", "internet_categorie","internet_reservations", "individus_masques", "blocage_impayes_off"]
        help_texts = {
            "internet_categorie": "Les catégories permettent par exemple d'attribuer des périodes de réservations à certains comptes internet uniquement.",
            "internet_reservations": "Décochez cette case pour interdire à cette individu d'accéder aux réservations sur le portail.",
            "individus_masques": "Vous pouvez sélectionner des membres de la individu qui n'apparaitront pas sur le portail."
        }

    def __init__(self, *args, **kwargs):
        idindividu = kwargs.pop("idindividu")
        individu = Individu.objects.get(pk=idindividu)
        if "instance" not in kwargs:
            self.instance = individu
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_portail_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        # Date d'expiration du mdp
        # if individu.utilisateur and hasattr(individu.utilisateur, 'date_expiration_mdp'):
        #     self.fields["internet_mdp"].widget.attrs["date_expiration_mdp"] = individu.utilisateur.date_expiration_mdp
        # else:
        #     self.fields["internet_mdp"].widget.attrs["date_expiration_mdp"] = None  # or a default value
        self.fields["internet_mdp"].widget.attrs["date_expiration_mdp"] = individu.utilisateur.date_expiration_mdp

        # Individus masqués
        individus = [rattachement.individu_id for rattachement in Rattachement.objects.filter(individu_id=idindividu)]
        self.fields["individus_masques"].queryset = Individu.objects.filter(pk__in=individus).order_by("nom")

        # Création des boutons de commande
        autres_commandes = [HTML("""
            <a type='button' class='btn btn-default' title="Envoyer les codes par Email" onclick="envoyer(mode='email')"><i class="fa fa-send-o margin-r-5"></i>Envoyer les codes par email</a> 
            <a type='button' class='btn btn-default' title="Envoyer les codes par SMS" onclick="envoyer(mode='sms')"><i class="fa fa-send-o margin-r-5"></i>Envoyer les codes par SMS</a> 
        """)]
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="individu_portail_modifier", modifier_args="idfamille=idfamille idindividu=idindividu",
                                  modifier=self.request.user.has_perm("core.individu_portail_modifier"), enregistrer=False, annuler=False, ajouter=False, autres_commandes=autres_commandes)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'individu_portail' idfamille=idfamille idindividu=idindividu %}", ajouter=False, autres_commandes=autres_commandes)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Hidden("idindividu", value=idindividu),
            Hidden("date_expiration_mdp", value=individu.utilisateur.date_expiration_mdp),
            Fieldset("Activation",
                Field("internet_actif"),
            ),
            Fieldset("Codes d'accès",
                Field("internet_identifiant"),
                Field("internet_mdp"),
                Field("date_expiration_mdp", type="hidden"),
            ),
            Fieldset("Options",
                Field("internet_categorie"),
                Field("internet_reservations"),
                Field("blocage_impayes_off"),
                Field("individus_masques"),
            ),
            HTML(EXTRA_HTML),
        )

EXTRA_HTML = """

<script>

    function regenerer_identifiant() {
        $.ajax({
            type: "POST",
            url: "{% url 'ajax_regenerer_identifiant_individu' %}",
            data: {
                idindividu: $('[name=idindividu]').val(),
                csrfmiddlewaretoken: "{{ csrf_token }}",
            },
            success: function (data) {
                $('#id_internet_identifiant').val(data.identifiant);
                toastr.success("Un nouvel identifiant a été généré");
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
                idindividu: $('[name=idindividu]').val(),
                csrfmiddlewaretoken: "{{ csrf_token }}",
            },
            success: function (data) {
                $("#id_internet_mdp").val(data.mdp);
                $("input[name='date_expiration_mdp']").val(data.date_expiration_mdp);
                verrouillage_ctrl();
                toastr.success("Un nouveau mot de passe a été généré");
            },
            error: function (data) {
                toastr.error(data.responseJSON.erreur);
            }
        });
    };

</script>

<br>

"""