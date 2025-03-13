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
from core.models import Activite, Rattachement, Groupe, PortailRenseignement
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from individus.utils import utils_pieces_manquantes
from core.models import Individu

class Formulaire_extra(FormulaireBase, forms.Form):
    groupe = forms.ModelChoiceField(label=_("Groupe"), queryset=Groupe.objects.all(), required=True,
                                    help_text=_("Sélectionnez le groupe correspondant à l'individu dans la liste."))

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
            pieces_necessaires = utils_pieces_manquantes.Get_liste_pieces_necessaires(activite=activite,
                                                                                      famille=famille,
                                                                                      individu=individu)
            for piece_necessaire in pieces_necessaires:
                if not piece_necessaire["valide"]:
                    nom_field = "document_%d" % piece_necessaire["type_piece"].pk
                    help_text = """Vous devez joindre ce document au format au pdf, jpg ou png. """
                    if piece_necessaire["document"]:
                        url_document_a_telecharger = piece_necessaire["document"].document.url
                        help_text += """Vous pouvez télécharger le document à compléter en cliquant sur le lien suivant : <a href='%s' target="_blank" title="Télécharger le document"><i class="fa fa-download margin-r-5"></i>Télécharger le document</a>.""" % url_document_a_telecharger
                    self.fields[nom_field] = forms.FileField(label=piece_necessaire["type_piece"].nom,
                                                             help_text=help_text, required=True, validators=[
                            FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg'])])
                    self.helper.layout.append(nom_field)


class Formulaire(FormulaireBase, ModelForm):
    activite = forms.ModelChoiceField(label=_("Activité"), queryset=Activite.objects.none(), required=True,
                                      help_text=_("Sélectionnez l'activité souhaitée dans la liste."))
    titre_historique = "Inscrire à une activité"
    template_name = "portail/edit.html"

    def Get_detail_historique(self, instance):
        return "Famille=%s, Individu=%s" % (instance.famille, instance.individu)
    class Meta:
        model = PortailRenseignement
        fields = "__all__"
        labels = {
            "famille": _("Famille"),
            "individu": _("Individu"),
        }
        help_texts = {
            "famille": _("Sélectionnez la famille."),
            "individu": _("Sélectionnez le membre de la famille à inscrire."),
        }

    def get_rattachements_for_user(self):
        rattachements = set()  # Use a set to avoid duplicates
        # Check if the user is part of a family or an individual
        if hasattr(self.request.user, 'individu'):
            # If the user is an individual, get all families they are attached to
            rattachements_query = Rattachement.objects.filter(individu=self.request.user.individu)
            rattachements.update(rattachements_query)

        elif hasattr(self.request.user, 'famille'):
            # If the user is part of a family, get rattachements for that family
            rattachements_query = Rattachement.objects.filter(famille=self.request.user.famille)
            rattachements.update(rattachements_query)

        return list(rattachements)  # Convert back to a list

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

        # Récupérer les rattachements pour l'utilisateur
        rattachements = self.get_rattachements_for_user()

        # Initialiser le champ famille avec '---------'
        familles = {(rattachement.famille_id, rattachement.famille.Get_nom()) for rattachement in rattachements}
        self.fields["famille"].choices = [('', '---------')] + list(familles)  # Ajouter '----' en premier choix

        # Initialiser le champ individu avec '----'
        famille_ids = {rattachement.famille_id for rattachement in rattachements}
        individus = Individu.objects.filter(rattachement__famille_id__in=famille_ids)
        self.fields["individu"].choices = [('', '---------')] + [
            (individu.idindividu, individu.Get_nom()) for individu in individus
        ]
        self.fields["famille"].required = True

        self.fields["individu"].required = True

        # Activité
        conditions = (
                Q(portail_inscriptions_affichage="TOUJOURS") |
                (
                        Q(portail_inscriptions_affichage="PERIODE") &
                        Q(portail_inscriptions_date_debut__lte=datetime.datetime.now()) &
                        Q(portail_inscriptions_date_fin__gte=datetime.datetime.now())
                )
        )
        self.fields["activite"].queryset = Activite.objects.filter(conditions).order_by("-date_fin", "nom")

        # Affichage
        self.helper.layout = Layout(
            Hidden("famille", value=self.request.user.famille.pk if hasattr(self.request.user, 'famille') else None),
            Hidden("etat", value="ATTENTE"),
            Hidden("categorie", value="activites"),
            Hidden("code", value="inscrire_activite"),
            Field("famille"),
            Field("individu"),
            Field("activite"),
            Div(id="form_extra"),
            HTML(EXTRA_SCRIPT),
            Commandes(
                enregistrer_label="<i class='fa fa-send margin-r-5'></i>%s" % _("Envoyer la demande d'inscription"),
                annuler_url="{% url 'portail_activites' %}",
                ajouter=False,
                aide=False,
                css_class="pull-right"
            ),
        )

EXTRA_SCRIPT = """
<script>
// Fonction pour actualiser le formulaire "extra" en fonction de l'activité sélectionnée
function On_change_activite() {
    var id_activite = $("#id_activite").val();
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
    On_change_activite();
    On_change_activite.call($('#id_activite').get(0));
});

$(document).ready(function() {
    // Soumission du formulaire d'inscription à une activité
    $("#portail_inscrire_activite_form").on('submit', function(event) {
        event.preventDefault();
        var formData = new FormData(this);  // Utiliser `this` pour pointer directement vers le formulaire
        formData.append("csrfmiddlewaretoken", "{{ csrf_token }}");

        $.ajax({
            type: "POST",
            url: "{% url 'portail_ajax_inscrire_valid_form' %}",
            data: formData,
            contentType: false,
            processData: false,
            dataType: "json",
            success: function(data) {
                window.location.href = data.url;
            },
            error: function(xhr) {
                toastr.error(xhr.responseJSON.erreur);
            }
        });
    });

    // Changement de la famille pour actualiser les individus
    $('#id_famille').change(function() {
        var selectedFamille = $(this).val();

        $.ajax({
            type: "POST",
            url: "{% url 'portail_ajax_inscrire_get_individus' %}",  // Récupérer les individus dynamiquement
            data: {
                'famille': selectedFamille,
                'csrfmiddlewaretoken': '{{ csrf_token }}'
            },
            success: function(data) {
                $('#id_individu').html(data);  // Update individual choices
            }
        });
    });

})

</script>
"""