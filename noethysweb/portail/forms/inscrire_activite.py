# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Div
from crispy_forms.bootstrap import Field
from core.models import Activite, Rattachement, Groupe, PortailRenseignement, Individu
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from individus.utils import utils_pieces_manquantes


class Formulaire_extra(FormulaireBase, forms.Form):
    groupe = forms.ModelChoiceField(label=_("Groupe"), queryset=Groupe.objects.all(), required=True, help_text=_("Sélectionnez le groupe correspondant à l'individu dans la liste."))

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

        # Affichage
        self.helper.layout = Layout(
            Field("groupe"),
        )

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

        self.Appliquer_version_bootstrap(5)


class Formulaire(FormulaireBase, ModelForm):
    activite = forms.ModelChoiceField(label=_("Activité"), queryset=Activite.objects.none(), required=True, help_text=_("Sélectionnez l'activité souhaitée dans la liste."))

    class Meta:
        model = PortailRenseignement
        fields = "__all__"
        labels = {
            "individu": _("Individu"),
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

        # Activité
        conditions = (Q(portail_inscriptions_affichage="TOUJOURS") | (Q(portail_inscriptions_affichage="PERIODE") & Q(portail_inscriptions_date_debut__lte=datetime.datetime.now()) & Q(portail_inscriptions_date_fin__gte=datetime.datetime.now())))
        activites = Activite.objects.filter(conditions).order_by("-date_fin", "nom")
        self.fields["activite"].queryset = activites

        # Individu
        rattachements = Rattachement.objects.select_related("individu").filter(famille=self.request.user.famille, individu__deces=False).exclude(individu__in=self.request.user.famille.individus_masques.all()).order_by("categorie")
        self.fields["individu"].queryset = Individu.objects.filter(pk__in=[rattachement.individu_id for rattachement in rattachements])
        self.fields["individu"].choices = [(None, "---------")] + [(rattachement.individu_id, rattachement.individu.Get_nom()) for rattachement in rattachements]
        self.fields["individu"].required = True

        # Éligibilité des individus pour chaque activité ouverte
        self.dict_categories = {rattachement.individu_id: rattachement.categorie for rattachement in rattachements}
        eligibilites = {}
        for activite in activites:
            motifs = {}
            for rattachement in rattachements:
                motif = activite.Get_motif_non_eligible_portail(individu=rattachement.individu, categorie=rattachement.categorie)
                if motif:
                    motifs[rattachement.individu_id] = str(motif)
            eligibilites[activite.pk] = {"masquer": activite.portail_inscriptions_non_eligibles == "MASQUER", "motifs": motifs}

        # Affichage
        self.helper.layout = Layout(
            Hidden("famille", value=self.request.user.famille.pk),
            Hidden("etat", value="ATTENTE"),
            Hidden("categorie", value="activites"),
            Hidden("code", value="inscrire_activite"),
            Field("activite"),
            Field("individu"),
            HTML("<div class='row'><div class='offset-md-2 col-md-10' id='bloc_non_eligibles' aria-live='polite'></div></div>"),
            Div(id="form_extra"),
            HTML("<script>var eligibilites = %s;</script>" % json.dumps(eligibilites)),
            HTML(EXTRA_SCRIPT),
            Commandes(enregistrer_label="<i class='fa fa-send margin-r-5'></i>%s" % _("Envoyer la demande d'inscription"), annuler_url="{% url 'portail_activites' %}", ajouter=False, aide=False, css_class="pull-right"),
        )
        self.Appliquer_version_bootstrap(5)

    def clean(self):
        cleaned_data = super().clean()
        activite, individu = cleaned_data.get("activite"), cleaned_data.get("individu")
        if activite and individu:
            motif = activite.Get_motif_non_eligible_portail(individu=individu, categorie=self.dict_categories.get(individu.pk))
            if motif:
                self.add_error("individu", _("Cet individu ne peut pas être inscrit à cette activité (%s)") % motif)
        return cleaned_data

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
// Filtre la liste des individus selon les conditions de l'activité sélectionnée
var options_individus = null;
function Actualiser_individus() {
    var select = $("#id_individu");
    if (options_individus === null) {
        options_individus = select.find("option").filter(function() { return $(this).val(); }).map(function() { return {id: $(this).val(), nom: $(this).text()}; }).get();
    }
    var valeur = select.val();
    var parametres = eligibilites[$("#id_activite").val()] || {masquer: false, motifs: {}};
    var nbre_eligibles = 0, non_eligibles = [];
    select.empty().append(new Option("---------", ""));
    $.each(options_individus, function(index, individu) {
        var motif = parametres.motifs[individu.id];
        if (!motif) {
            nbre_eligibles += 1;
            select.append(new Option(individu.nom, individu.id, false, individu.id == valeur));
        } else {
            non_eligibles.push({nom: individu.nom, motif: motif});
            if (!parametres.masquer) {
                select.append($("<option>", {value: individu.id, disabled: true, text: individu.nom + " (" + motif.toLowerCase() + ")"}));
            }
        }
    });

    // Message d'information
    var bloc = $("#bloc_non_eligibles").empty();
    if ($("#id_activite").val() && nbre_eligibles === 0) {
        bloc.html("<div class='alert alert-warning'><i class='fa fa-exclamation-triangle margin-r-5' aria-hidden='true'></i>" + "Aucun membre de votre famille ne remplit les conditions d'inscription à cette activité." + "</div>");
    } else if (non_eligibles.length && !parametres.masquer) {
        var liste = $("<ul class='mb-0'>");
        $.each(non_eligibles, function(index, item) { liste.append($("<li>").text(item.nom + " : " + item.motif)); });
        bloc.append($("<div class='alert alert-light border'>").append("<i class='fa fa-info-circle margin-r-5' aria-hidden='true'></i>Non éligibles à cette activité :", liste));
    }
    $("#portail_inscrire_activite_form button[type='submit']").prop("disabled", $("#id_activite").val() && nbre_eligibles === 0);
};

$(document).ready(function() {
    $('#id_activite').change(function() {
        Actualiser_individus();
        On_change_activite();
    });
    $('#id_individu').change(On_change_activite);
    Actualiser_individus();
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
