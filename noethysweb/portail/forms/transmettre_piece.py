# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML
from crispy_forms.bootstrap import Field
from core.models import Piece, Rattachement, Individu
from core.utils.utils_commandes import Commandes
from portail.forms.fiche import FormulaireBase
from individus.utils import utils_pieces_manquantes
from core.models import Famille


class Formulaire(FormulaireBase, ModelForm):
    # Type de pièce
    selection_piece = forms.TypedChoiceField(label=_("Type de document"), choices=[], required=True, help_text=_(
        "Sélectionnez un type de document dans la liste. Sélectionnez 'Autre type' s'il ne s'agit pas d'un document prédéfini."))
    individu = forms.TypedChoiceField(label=_("Individu concerné"), choices=[], required=False, help_text=_(
        "Sélectionnez le nom de l'individu concerné ou la famille s'il s'agit d'un document qui concerne toute la famille."))
    document = forms.FileField(label=_("Document"),
                               help_text=_("Sélectionnez un document à joindre (pdf, jpg ou png)."), required=True,
                               validators=[FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg'])])
    famille = forms.ModelChoiceField(
        queryset=Famille.objects.all(),  # Initialement vide
        label=_("Famille concernée"),
        required=True,
        help_text=_("Sélectionnez la famille concernée par le document.")
    )

    class Meta:
        model = Piece
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            "titre": _("Titre du document*"),
            "observations": _("Observations"),
        }
        help_texts = {
            "titre": _("Saisissez un titre pour ce document. Ex : Certificat médical de Sophie..."),
            "observations": _("Vous pouvez ajouter des observations si vous le souhaitez."),
        }

    def get_rattachements_for_user(self):
        rattachements = set()  # Set pour éviter les doublons
        # Vérifiez si l'utilisateur fait partie d'une famille ou d'un individu
        if hasattr(self.request.user, 'individu'):
            # Si l'utilisateur est un individu, obtenez toutes les familles auxquelles il est rattaché
            rattachements_query = Rattachement.objects.filter(individu=self.request.user.individu)
            rattachements.update(rattachements_query)

        elif hasattr(self.request.user, 'famille'):
            # Si l'utilisateur fait partie d'une famille, obtenir les pièces jointes pour cette famille
            rattachements_query = Rattachement.objects.filter(famille=self.request.user.famille)
            rattachements.update(rattachements_query)
        return list(rattachements)  # Reconvertir en liste

    def __init__(self, *args, **kwargs):
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'portail_transmettre_piece_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False
        familles = []
        # Gérer le cas où l'utilisateur fait directement partie d'une famille
        if hasattr(self.request.user, 'famille'):
            familles.append(self.request.user.famille)
        # Gérer le cas où l'utilisateur est un individu et lié via Rattachement
        elif hasattr(self.request.user, 'individu'):
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            # Ajoutez chaque famille liée à la liste
            for rattachement in rattachements:
                if rattachement.famille and rattachement.titulaire == 1:
                    familles.append(rattachement.famille)

        # Vérifier si des familles existent avant de procéder
        if familles:
            for famille in familles:
                # Pièces à fournir
                self.liste_pieces_fournir = utils_pieces_manquantes.Get_pieces_manquantes(famille=famille,
                                                                                          exclure_individus=famille.individus_masques.all())
                self.fields['selection_piece'].choices = [(index, piece["label"]) for index, piece in
                                                          enumerate(self.liste_pieces_fournir)] + [
                                                             (9999, "Un autre type de pièce")]
                self.fields['selection_piece'].initial = None

                # Récupérer les rattachements pour l'utilisateur
                rattachements = self.get_rattachements_for_user()
                familless = {(rattachement.famille_id, rattachement.famille.Get_nom()) for rattachement in rattachements
                             if rattachement.famille and rattachement.titulaire == 1}
                if len(familless) > 1:
                    self.fields['famille'].choices = [(None, "------------")] + list(familless)
                    self.fields['individu'].choices = [(None, "La famille")]
                else:
                    self.fields['famille'].choices = list(familless)
                famille_ids = {rattachement.famille_id for rattachement in rattachements if
                               rattachement.famille and rattachement.titulaire == 1}
                individus = Individu.objects.filter(rattachement__famille_id__in=famille_ids)
                self.fields['individu'].choices = [(None, "La famille")] + [
                    (individu.idindividu, individu.Get_nom()) for individu in individus
                ]
                # Auteur
                if not self.instance.pk:
                    self.fields["auteur"].initial = self.request.user
                # Affichage
                self.helper.layout = Layout(
                    Hidden("famille", value=famille.pk),
                    Field("auteur", type="hidden"),
                    Field('selection_piece'),
                    Field('titre'),
                    Field('famille'),
                    Field('individu'),
                    Field('document'),
                    Field('observations'),
                    HTML(EXTRA_SCRIPT),
                    Commandes(enregistrer_label="<i class='fa fa-send margin-r-5'></i>%s" % _("Envoyer"),
                              annuler_url="{% url 'portail_documents' %}", ajouter=False, aide=False,
                              css_class="pull-right"),
                )

    def clean(self):
        # Type de pièce
        if int(self.cleaned_data["selection_piece"]) == 9999:
            if self.cleaned_data["titre"] in ("", None):
                self.add_error('titre', "Vous devez saisir un titre pour cette pièce !")
            piece = None
        else:
            piece = self.liste_pieces_fournir[int(self.cleaned_data["selection_piece"])]

        self.cleaned_data["type_piece"] = piece["type_piece"] if piece else None

        # Individu
        if piece:
            # Si pièce prédéfinie
            self.cleaned_data["individu"] = None if piece["type_piece"].public == "famille" else piece["individu"]
        else:
            # Si pièce libre
            self.cleaned_data["individu"] = Individu.objects.get(pk=self.cleaned_data["individu"]) if self.cleaned_data[
                "individu"] else None

        # Famille
        if piece and piece["type_piece"].public == "individu" and piece["type_piece"].valide_rattachement:
            self.cleaned_data["famille"] = None

        # Durée de validité
        self.cleaned_data["date_debut"] = datetime.date.today()
        self.cleaned_data["date_fin"] = piece["type_piece"].Get_date_fin_validite() if piece else datetime.date(2999, 1,
                                                                                                                1)

        return self.cleaned_data


EXTRA_SCRIPT = """
<script>


// Sélection pièce
function On_change_selection_piece(event) {
    $('#div_id_titre').hide();
    $('#div_id_choix_individu').hide();
    if (this.value == 9999) {
        $('#div_id_titre').show();
        $('#div_id_choix_individu').show();
    };
}
$(document).ready(function() {
    $('#id_selection_piece').change(On_change_selection_piece);
    On_change_selection_piece.call($('#id_selection_piece').get(0));

    // Changement de la famille pour actualiser les individus
    $('#id_famille').change(function() {
        var selectedFamille = $(this).val();

        $.ajax({
            type: "POST",
            url: "{% url 'portail_ajax_inscrire_get_individus_by_famille' %}",  // Récupérer les individus dynamiquement
            data: {
                'famille': selectedFamille,
                'csrfmiddlewaretoken': '{{ csrf_token }}'
            },
            success: function(data) {
                $('#id_individu').html('<option value="">La famille</option>' + data);  // Met à jour la liste des individus
            },
            error: function(xhr, status, error) {
                console.log("Erreur lors de la récupération des individus :", error);
            }
        });
    });
});
</script>
"""
