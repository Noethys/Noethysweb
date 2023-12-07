# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from core.forms.select2 import Select2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML
from crispy_forms.bootstrap import Field
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Recu, ModeleDocument
from core.widgets import DatePickerWidget

TEXTE_INTRO_DEFAUT = "Je soussigné(e) {SIGNATAIRE}, certifie avoir reçu pour la famille de {FAMILLE} la somme de {MONTANT}."


class Formulaire(FormulaireBase, ModelForm):
    date_edition = forms.DateField(label="Date d'édition", required=True, widget=DatePickerWidget(attrs={'afficher_fleches': True}))
    modele = forms.ModelChoiceField(label="Modèle de document", widget=Select2Widget(), queryset=ModeleDocument.objects.filter(categorie="reglement").order_by("nom"), required=True)
    signataire = forms.CharField(label="Signataire", required=True)
    intro = forms.CharField(label="Introduction", widget=forms.Textarea(attrs={'rows': 4}), required=True)
    afficher_prestations = forms.BooleanField(label="Inclure la liste des prestations payées avec ce règlement", required=False)

    class Meta:
        model = Recu
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        idreglement = kwargs.pop("idreglement", None)
        utilisateur = kwargs.pop("utilisateur", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'recu_reglements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Utilisateur
        self.fields["utilisateur"].initial = self.request.user

        # Date d'édition
        self.fields["date_edition"].initial = datetime.date.today()

        # Numéro
        self.fields["numero"].initial = 1
        if not self.instance.idrecu:
            dernier_recu = Recu.objects.last()
            if dernier_recu:
                self.fields["numero"].initial = dernier_recu.numero + 1

        # Charge le modèle de document par défaut
        modele_defaut = ModeleDocument.objects.filter(categorie="reglement", defaut=True).first()
        if modele_defaut:
            self.fields["modele"].initial = modele_defaut

        # Signataire
        if utilisateur:
            self.fields["signataire"].initial = utilisateur.get_full_name() or utilisateur.get_short_name() or utilisateur

        # Introduction
        self.fields["intro"].initial = TEXTE_INTRO_DEFAUT
        self.fields['intro'].help_text = "Mots-clés disponibles : {SIGNATAIRE}, {FAMILLE}, {MONTANT}, {DATE_REGLEMENT}, {MODE_REGLEMENT}, {NOM_PAYEUR}."

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'famille_reglements_liste' idfamille=idfamille %}", ajouter=False,
                autres_commandes=[
                    HTML("""<a type='button' class='btn btn-default' title="Envoyer par Email" onclick="impression_pdf(true, false)" href='#'><i class="fa fa-send-o margin-r-5"></i>Envoyer par email</a> """),
                    HTML("""<a type='button' class='btn btn-default' title="Aperçu PDF" href='#' onclick="impression_pdf(false, true)"><i class="fa fa-file-pdf-o margin-r-5"></i>Aperçu PDF</a> """),
                ]),
            Hidden('famille', value=idfamille),
            Hidden('reglement', value=idreglement),
            Field("date_edition"),
            Field("numero"),
            Field("modele"),
            Field("signataire"),
            Field("intro"),
            Field("afficher_prestations"),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        return self.cleaned_data


EXTRA_HTML = """

{# Insertion des modals #}
{% include 'outils/modal_editeur_emails.html' %}
{% include 'core/modal_pdf.html' %}

<script>

// Impression du PDF
function impression_pdf(email=false) {
    $.ajax({
        type: "POST",
        url: "{% url 'ajax_recu_impression_pdf' %}",
        data: {
            idreglement: $("input:hidden[name='reglement']").val(),
            date_edition: $("#id_date_edition").val(),
            numero: $("#id_numero").val(),
            modele: $("#id_modele").val(),
            signataire: $("#id_signataire").val(),
            intro: $("#id_intro").val(),
            afficher_prestations: $("#id_afficher_prestations").prop("checked"),
            idfamille: {{ idfamille }},
            csrfmiddlewaretoken: "{{ csrf_token }}",
        },
        datatype: "json",
        success: function(data){
            if (email) {
                envoyer_email(data);
            } else {
                charge_pdf(data);
            }
        },
        error: function(data) {
            toastr.error(data.responseJSON.erreur);
        }
    })
};

</script>

"""