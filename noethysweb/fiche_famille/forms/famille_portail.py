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
from fiche_famille.widgets import Internet_identifiant, Internet_mdp


class Formulaire(FormulaireBase, ModelForm):
    internet_identifiant = forms.CharField(label="Identifiant", required=False, widget=Internet_identifiant(), help_text="Identifiant de connexion au portail, généré automatiquement. Il est déconseillé de le modifier.")
    internet_mdp = forms.CharField(label="Mot de passe", required=False, widget=Internet_mdp(), help_text="Des étoiles ***** signifient que la famille a personnalisé son mot de passe lors de sa première connexion. Il n'est alors plus consultable : si la famille l'a oublié, générez-en un nouveau.")
    date_expiration_mdp = forms.DateTimeField(label="Date d'expiration", required=False, help_text="Date limite d'utilisation du mot de passe généré. Elle est supprimée dès que la famille personnalise son mot de passe.")
    individus_masques = forms.ModelMultipleChoiceField(label="Individus masqués", widget=Select2MultipleWidget({"lang": "fr", "data-width": "100%"}), queryset=Individu.objects.none(), required=False, help_text="Les membres sélectionnés n'apparaîtront pas sur le portail (par exemple un individu qui ne fréquente plus la structure).")

    class Meta:
        model = Famille
        fields = ["internet_actif", "internet_identifiant", "internet_mdp", "internet_categorie", "internet_reservations", "individus_masques", "blocage_impayes_off"]
        help_texts = {
            "internet_actif": "Décochez cette case pour empêcher la famille de se connecter au portail.",
            "blocage_impayes_off": "Cochez pour laisser cette famille réserver sur le portail même si elle a des impayés et que le blocage des impayés est activé.",
            "internet_categorie": "Facultatif : la catégorie permet par exemple d'ouvrir certaines périodes de réservation à un groupe de familles seulement.",
            "internet_reservations": "Décochez cette case pour empêcher la famille de réserver depuis le portail. Elle garde l'accès aux autres pages.",
            "individus_masques": "Les membres sélectionnés n'apparaîtront pas sur le portail (par exemple un individu qui ne fréquente plus la structure)."
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        famille = Famille.objects.get(pk=idfamille)
        if "instance" not in kwargs:
            self.instance = famille
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_portail_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date d'expiration du mdp
        self.fields["internet_mdp"].widget.attrs["date_expiration_mdp"] = famille.utilisateur.date_expiration_mdp

        # Individus masqués
        individus = [rattachement.individu_id for rattachement in Rattachement.objects.filter(famille_id=idfamille)]
        self.fields["individus_masques"].queryset = Individu.objects.filter(pk__in=individus).order_by("nom")

        # Création des boutons de commande
        autres_commandes = [HTML("""
            <a type='button' class='btn btn-default' title="Envoyer les codes par Email" onclick="envoyer(mode='email')"><i class="fa fa-send-o margin-r-5"></i>Envoyer les codes par email</a> 
            <a type='button' class='btn btn-default' title="Envoyer les codes par SMS" onclick="envoyer(mode='sms')"><i class="fa fa-send-o margin-r-5"></i>Envoyer les codes par SMS</a> 
        """)]
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="famille_portail_modifier", modifier_args="idfamille=idfamille",
                                  modifier=self.request.user.has_perm("core.famille_portail_modifier"), enregistrer=False, annuler=False, ajouter=False, autres_commandes=autres_commandes)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'famille_portail' idfamille=idfamille %}", ajouter=False, autres_commandes=autres_commandes)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Hidden("idfamille", value=idfamille),
            Hidden("date_expiration_mdp", value=famille.utilisateur.date_expiration_mdp),
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
            url: "{% url 'ajax_regenerer_identifiant' %}",
            data: {
                idfamille: $('[name=idfamille]').val(),
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
                idfamille: $('[name=idfamille]').val(),
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