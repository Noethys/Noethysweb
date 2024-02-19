# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Div
from crispy_forms.bootstrap import Field
from core.models import Activite, Rattachement, Groupe, PortailRenseignement, CategorieTarif
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from individus.utils import utils_pieces_manquantes


class Formulaire_extra(FormulaireBase, forms.Form):
    groupe = forms.ModelChoiceField(label=_("Groupe"), queryset=Groupe.objects.all(), required=True, help_text=_("Sélectionnez le groupe correspondant à l'individu dans la liste."))
    categorie_tarif = forms.ModelChoiceField(label=_("Catégorie de Tarif"), queryset=CategorieTarif.objects.none(), required=True, help_text=_("Sélectionnez le nombre d'enfants inscrits à un camp à pédagogie Flambeaux."))

    def __init__(self, *args, **kwargs):
        activite = kwargs.pop("activite", None)
        famille = kwargs.pop("famille", None)
        individu = kwargs.pop("individu", None)
        super(Formulaire_extra, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_inscrire_activite_extra_form'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        self.helper.form_tag = False

        # Recherche des groupes de l'activité
        liste_groupes = Groupe.objects.filter(activite=activite).order_by("nom")
        self.fields["groupe"].queryset = liste_groupes

        # S'il n'y a qu'un groupe dans l'activité, on le sélectionne par défaut
        if len(liste_groupes) == 1:
            self.fields["groupe"].initial = liste_groupes.first()

        # Recherche des catégories de tarif de l'activité
        liste_categorie_tarif = CategorieTarif.objects.filter(activite=activite).order_by("nom")
        self.fields["categorie_tarif"].queryset = liste_categorie_tarif

        # S'il n'y a qu'une catégorie de tarif, on le sélectionne par défaut
        if len(liste_categorie_tarif) == 1:
            self.fields["categorie_tarif"].initial = liste_categorie_tarif.first()

        # Ajout des pièces à fournir
        if activite.portail_inscriptions_imposer_pieces:
            pieces_necessaires = utils_pieces_manquantes.Get_liste_pieces_necessaires(activite=activite, famille=famille, individu=individu)
            for piece_necessaire in pieces_necessaires:
                if not piece_necessaire["valide"]:
                    nom_field = "document_%d" % piece_necessaire["type_piece"].pk
                    help_text = """Vous devez joindre ce document au format au pdf, jpg ou png. """
                    if piece_necessaire["document"]:
                        url_document_a_telecharger = piece_necessaire["document"].document.url
                        help_text += """Vous pouvez télécharger le document à compléter en cliquant sur le lien suivant : <a href='%s' target="_blank" title="Télécharger le document"><i class="fa fa-download margin-r-5"></i>Télécharger le document</a>.""" % url_document_a_telecharger
                    self.fields[nom_field] = forms.FileField(label=piece_necessaire["type_piece"].nom, help_text=help_text, required=True, validators=[FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg'])])
                    self.helper.layout.append(nom_field)


class Formulaire(FormulaireBase, ModelForm):
    activite = forms.ModelChoiceField(label=_("Activité"), queryset=Activite.objects.none(), required=True, help_text=_("Sélectionnez l'activité souhaitée dans la liste."))

    class Meta:
        model = PortailRenseignement
        fields = "__all__"
        labels = {
            "individu": _("Individu"),
            "categorie_tarif": _("Catégorie de Tarif"),
        }
        help_texts = {
            "individu": _("Sélectionnez le membre de la famille à inscrire."),
        }

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_inscrire_activite_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False
        self.helper.attrs = {'enctype': 'multipart/form-data'}

        # Individu
        rattachements = Rattachement.objects.select_related("individu").filter(
            famille=self.request.user.famille).exclude(
            individu__in=self.request.user.famille.individus_masques.all()).order_by("categorie")
        self.fields["individu"].choices = [(rattachement.individu_id, rattachement.individu.Get_nom()) for rattachement
                                           in rattachements]
        self.fields["individu"].required = True

        # Activité
        conditions = (Q(portail_inscriptions_affichage="TOUJOURS") | (Q(portail_inscriptions_affichage="PERIODE") & Q(
            portail_inscriptions_date_debut__lte=datetime.datetime.now()) & Q(
            portail_inscriptions_date_fin__gte=datetime.datetime.now())))
        self.fields["activite"].queryset = Activite.objects.filter(conditions).order_by("nom")

        # Affichage
        self.helper.layout = Layout(
            Hidden("famille", value=self.request.user.famille.pk),
            Hidden("etat", value="ATTENTE"),
            Hidden("categorie", value="activites"),
            Hidden("code", value="inscrire_activite"),
            Field("individu"),
            Field("activite"),
            Div(id="form_extra"),
            HTML(EXTRA_SCRIPT),
            Commandes(
                enregistrer_label="<i class='fa fa-send margin-r-5'></i>%s" % _("Envoyer la demande d'inscription"),
                annuler_url="{% url 'portail_activites' %}", ajouter=False, aide=False, css_class="pull-right"),
        )


EXTRA_SCRIPT = """
<script>

// Actualise le form extra en fonction de l'activité sélectionnée
function On_change_activite() {
    var idactivite = $("#id_activite").val();
    $.ajax({ 
        type: "POST",
        url: "{% url 'portail_ajax_inscrire_get_form_extra' %}",
        data: $("#portail_inscrire_activite_form").serialize(),
        success: function (data) { 
            $("#form_extra").html(data['form_html']);
        }
    });
};
$(document).ready(function() {
    $('#id_activite').change(On_change_activite);
    On_change_activite.call($('#id_activite').get(0));
});

$(document).ready(function() {
    $("#portail_inscrire_activite_form").on('submit', function (event) {
        event.preventDefault();
        var formData = new FormData($("#portail_inscrire_activite_form")[0]);
        formData.append("csrfmiddlewaretoken", "{{ csrf_token }}");
        $.ajax({
            type: "POST",
            url: "{% url 'portail_ajax_inscrire_valid_form' %}",
            data: formData,
            contentType: false,
            processData: false,
            datatype: "json",
            success: function(data){
                window.location.href = data.url;
            },
            error: function(data) {
                toastr.error(data.responseJSON.erreur);
            }
        });
    });
})
</script>
"""
