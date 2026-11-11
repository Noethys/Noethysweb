# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import re
from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import PesModele, ModeleDocument, CHOIX_FORMAT_EXPORT_TRESOR


# Valeurs proposées pour le format PES ORMC
CHOIX_EDITION_ASAP_PES = [
    ("", "Aucune balise Edition"),
    ("04", "04-ASAP sans traitement DGFIP"),
]
CHOIX_TYPE_PJ_PES = [
    ("007", "007-Facture ORMC"),
    ("010", "010-Facture ASAP associée à un ORMC (en PDF) hors Chorus"),
    ("002", "002-Recette"),
]


# Organisation commune des formulaires de modèles d'export : (titre du cadre, [(champ, formats concernés)]).
# Chaque format n'affiche que les champs lus par son export. Un cadre sans champ affiché est masqué.
TOUS_FORMATS = ("pes", "magnus", "jvs", "corail")
CADRES_FORMULAIRE = [
    ("Généralités", [
        ("format", TOUS_FORMATS),
        ("nom", TOUS_FORMATS),
        ("observations", TOUS_FORMATS),
    ]),
    ("Collectivité et trésorerie", [
        ("id_collectivite", ("pes", "jvs")),
        ("nom_collectivite", ("jvs", "corail")),
        ("code_collectivite", ("pes", "magnus", "jvs")),
        ("code_budget", ("pes", "magnus", "jvs")),
        ("id_poste", ("pes",)),
        ("code_etab", ("pes",)),
    ]),
    ("Imputation par défaut", [
        ("id_poste", ("magnus", "jvs", "corail")),
        ("code_prodloc", TOUS_FORMATS),
        ("operation", ("magnus",)),
        ("fonction", ("magnus", "jvs", "corail")),
        ("service1", ("magnus", "jvs", "corail")),
        ("service2", ("magnus", "jvs", "corail")),
    ]),
    ("Titres et avis des sommes à payer", [
        ("objet_dette", ("pes", "corail")),
        ("edition_asap", ("pes", "magnus", "jvs")),
        ("inclure_detail", ("magnus", "corail")),
        ("detail_deductions", ("jvs",)),
        ("payable_internet", ("magnus",)),
        ("nom_tribunal", ("magnus",)),
    ]),
    ("Tiers", [
        ("code_compta_as_alias", ("magnus",)),
        ("inclure_tiers_solidaires", ("magnus", "corail")),
    ]),
    ("Pièces jointes", [
        ("inclure_pieces_jointes", ("pes", "magnus", "corail")),
        ("modele_document", ("pes", "magnus", "corail")),
        ("type_pj", ("pes", "magnus")),
    ]),
    ("Libellés", [
        ("objet_piece", TOUS_FORMATS),
        ("prestation_libelle", ("magnus", "jvs", "corail")),
        ("prelevement_libelle", TOUS_FORMATS),
    ]),
    ("Compte et règlement automatique", [
        ("compte", TOUS_FORMATS),
        ("reglement_auto", TOUS_FORMATS),
        ("mode", TOUS_FORMATS),
    ]),
]


class Formulaire_creation(FormulaireBase, forms.Form):
    format = forms.ChoiceField(label="Format", choices=CHOIX_FORMAT_EXPORT_TRESOR, required=True, help_text="Sélectionnez le format du fichier d'export selon le logiciel ou l'organisme destinataire : PES v2 pour la DGFiP, Magnus pour Berger-Levrault, Millésime pour JVS ou Corail pour Cosoluce.")

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Recherche le dernier format utilisé
        lot = PesModele.objects.last()
        if lot:
            self.fields["format"].initial = lot.format

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Sélection du format",
                Field("format"),
            ),
        )


class Formulaire(FormulaireBase, ModelForm):
    modele_document = forms.ModelChoiceField(label="Modèle de facture", queryset=ModeleDocument.objects.filter(categorie="facture").order_by("nom"), required=False)

    class Meta:
        model = PesModele
        fields = "__all__"
        widgets = {
            "observations": forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            "nom": "Saisissez le nom du modèle d'export. Exemple : Export cantine vers la trésorerie.",
            "observations": "Vous pouvez saisir ici des informations complémentaires sur ce modèle.",
            "format": "Format du fichier d'export, choisi selon le logiciel ou l'organisme destinataire.",
            "id_poste": "Saisissez le code du poste comptable fourni par votre trésorerie (7 caractères maximum). Il peut être remplacé par le code comptable de l'activité ou de la prestation.",
            "id_collectivite": "Saisissez l'identifiant de la collectivité, généralement son numéro SIRET (14 chiffres).",
            "code_collectivite": "Saisissez le code de la collectivité fourni par votre trésorerie.",
            "code_budget": "Saisissez le code du budget fourni par votre trésorerie. Exemple : 01 pour le budget principal.",
            "code_prodloc": "Saisissez le code produit local (4 caractères maximum). Il peut être remplacé par le code produit local de l'activité ou de la prestation.",
            "code_etab": "Saisissez le code établissement fourni par votre trésorerie. Il est utilisé pour composer la référence des titres.",
            "objet_dette": "Saisissez l'objet de la dette qui figurera sur les titres. Vous pouvez utiliser des mots-clés comme {MOIS_LETTRES} ou {ANNEE}.",
        }

    def __init__(self, *args, **kwargs):
        format = kwargs.pop("format", None)
        if kwargs.get("instance", None):
            format = kwargs["instance"].format
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'lots_pes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Format
        self.fields["format"].disabled = True
        if not self.instance.pk:
            self.fields["format"].initial = format

        # PES ORMC : valeurs et libellés propres au PES
        if format == "pes":
            self.fields["edition_asap"].choices = CHOIX_EDITION_ASAP_PES
            self.fields["edition_asap"].label = "Balise Edition"
            self.fields["edition_asap"].help_text = "Valeur de la balise Edition de chaque article de rôle. Avec 04, la DGFiP n'édite pas d'avis des sommes à payer : la collectivité envoie elle-même ses factures et le comptable les consulte dans Hélios. Les factures PDF doivent alors être jointes."
            self.fields["type_pj"].choices = CHOIX_TYPE_PJ_PES
            self.fields["type_pj"].help_text = "Type de pièce jointe (balise TypePJ des blocs PJRef et PES_PJ). Faites confirmer la valeur attendue par votre poste comptable."
            self.fields["inclure_pieces_jointes"].label = "Joindre les factures PDF"
            self.fields["inclure_pieces_jointes"].help_text = "Cochez cette case pour intégrer les factures PDF dans le fichier PES (bloc PES_PJ) et les référencer dans chaque article de rôle (bloc PJRef)."
            if not self.instance.pk:
                self.fields["edition_asap"].initial = ""
                self.fields["type_pj"].initial = "007"
                self.fields["inclure_pieces_jointes"].initial = False

        # Libellés et aides selon le sens du champ dans chaque format
        if format == "pes":
            self.fields["id_poste"].label = "Poste comptable"
            self.fields["id_poste"].help_text = "Saisissez le codique DGFiP de votre trésorerie : 6 ou 7 chiffres (balise IdPost). Exemple : 029012."
        elif format in ("magnus", "jvs", "corail"):
            self.fields["id_poste"].label = "Article par défaut"
            self.fields["id_poste"].help_text = "Saisissez l'article (nature) d'imputation de la recette. Il peut être remplacé par le code comptable de l'activité ou de la prestation."
        if format == "magnus":
            self.fields["id_poste"].help_text = "Saisissez l'article (nature) d'imputation de la recette, 10 caractères maximum. Il peut être remplacé par le code comptable de l'activité ou de la prestation."
            self.fields["code_collectivite"].help_text = "Saisissez le code de la collectivité dans Magnus (10 caractères maximum)."
        self.fields["compte"].help_text = "Sélectionnez le compte bancaire à créditer lors du règlement automatique et des prélèvements."
        self.fields["operation"].help_text = "Code de l'opération d'imputation (facultatif)."
        self.fields["fonction"].help_text = "Code de la fonction d'imputation (facultatif)."
        self.fields["nom_tribunal"].help_text = "Nom du tribunal administratif de recours, mentionné sur l'avis des sommes à payer."

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'modeles_pes_liste' %}"),
            *self.Get_cadres(format),
            HTML(EXTRA_SCRIPT),
        )

    def Get_cadres(self, format):
        """ Construit les cadres du formulaire selon l'organisation commune CADRES_FORMULAIRE """
        format_connu = format in TOUS_FORMATS
        cadres, champs_affiches = [], set()
        for titre, champs in CADRES_FORMULAIRE:
            noms = []
            for nom, formats in champs:
                # Un format inconnu affiche tous les champs (une seule fois chacun)
                if (format in formats or not format_connu) and nom not in champs_affiches:
                    noms.append(nom)
                    champs_affiches.add(nom)
            if noms:
                cadres.append(Fieldset(titre, *[Field(nom) for nom in noms]))

        # Les champs non utilisés par ce format restent dans le formulaire, cachés, pour conserver leurs valeurs.
        # Ils sont désactivés : Django reprend alors la valeur enregistrée sans tenir compte de la saisie,
        # et un champ invisible ne peut jamais bloquer l'enregistrement (champ obligatoire vide par exemple).
        champs_caches = [nom for nom in self.fields if nom not in champs_affiches]
        for nom in champs_caches:
            self.fields[nom].required = False
            self.fields[nom].disabled = True
        cadres.extend([Field(nom, type="hidden") for nom in champs_caches])
        return cadres

    def clean(self):
        # Copie des valeurs : add_error() retire le champ de cleaned_data, et un champ déjà invalide (valeur trop longue,
        # choix hors liste...) n'y figure pas. Les contrôles ci-dessous ne doivent donc jamais lire cleaned_data directement.
        donnees = dict(self.cleaned_data)
        format = donnees.get("format")

        def Manquant(nom):
            """ Le champ est vide et n'a pas déjà une erreur de saisie """
            return nom not in self.errors and not donnees.get(nom)

        def Valide(nom):
            """ Le champ est renseigné et n'a pas déjà une erreur de saisie """
            return nom not in self.errors and bool(donnees.get(nom))

        if Manquant("id_collectivite") and format in ("pes", "jvs"):
            self.add_error("id_collectivite", "Vous devez renseigner l'identifiant de la collectivité")

        if Manquant("code_collectivite") and format in ("magnus", "pes", "jvs"):
            self.add_error("code_collectivite", "Vous devez renseigner le code collectivité")

        if Manquant("code_budget") and format in ("magnus", "pes", "jvs"):
            self.add_error("code_budget", "Vous devez renseigner le code budget")

        if Manquant("id_poste") and format in ("magnus", "pes", "jvs", "corail"):
            self.add_error("id_poste", "Vous devez renseigner le poste")

        # PES ORMC : formats imposés par le schéma PES (IdPost et CodBud)
        if format == "pes":
            if Valide("id_poste") and not re.fullmatch(r"02[A-B][0-9]{3,4}|[0-9]{6,7}", donnees["id_poste"].strip()):
                self.add_error("id_poste", "Le poste comptable doit être le codique DGFiP de la trésorerie : 6 ou 7 chiffres (exemple : 029012)")
            if Valide("code_budget") and not re.fullmatch(r"[0-9A-Z][0-9]", donnees["code_budget"].strip()):
                self.add_error("code_budget", "Le code budget doit comporter 2 caractères : une lettre majuscule ou un chiffre, suivi d'un chiffre (exemple : 00 pour le budget principal)")

        # Magnus : longueurs maximales des colonnes du fichier d'import (sinon la valeur serait tronquée à l'export)
        if format == "magnus":
            for nom, longueur, libelle in (("code_collectivite", 10, "Le code collectivité"), ("id_poste", 10, "L'article")):
                if Valide(nom) and len(donnees[nom]) > longueur:
                    self.add_error(nom, "%s ne doit pas dépasser %d caractères (format Magnus)" % (libelle, longueur))

        if Manquant("code_prodloc") and format in ("magnus", "pes", "jvs", "corail"):
            self.add_error("code_prodloc", "Vous devez renseigner le code produit local")

        if Manquant("code_etab") and format in ("pes",):
            self.add_error("code_etab", "Vous devez renseigner le code établissement")

        if Manquant("objet_dette") and format in ("pes", "corail"):
            self.add_error("objet_dette", "Vous devez renseigner l'objet de la dette")

        if Manquant("modele_document") and format in ("magnus", "corail", "pes") and donnees.get("inclure_pieces_jointes"):
            self.add_error("modele_document", "Vous devez sélectionner un modèle de facture")

        if format == "pes" and Valide("edition_asap") and not donnees.get("inclure_pieces_jointes"):
            self.add_error("edition_asap", "La balise Edition impose de joindre les factures PDF (bloc PJRef obligatoire)")

        if format == "pes" and donnees.get("inclure_pieces_jointes") and Manquant("type_pj"):
            self.add_error("type_pj", "Vous devez sélectionner le type de pièce jointe")

        if Manquant("nom_collectivite") and format in ("jvs", "corail"):
            self.add_error("nom_collectivite", "Vous devez renseigner le nom de la collectivité")

        return self.cleaned_data

EXTRA_SCRIPT = """
<script>

// Règlement automatique
function On_change_reglement_auto() {
    $('#div_id_mode').hide();
    if ($(this).prop("checked")) {
        $('#div_id_mode').show();
    }
}
$(document).ready(function() {
    $('#id_reglement_auto').change(On_change_reglement_auto);
    On_change_reglement_auto.call($('#id_reglement_auto').get(0));
});

// Pièces jointes : le modèle de facture et le type de PJ ne sont affichés que si les factures PDF sont incluses
function On_change_inclure_pieces_jointes() {
    var format = $('#id_format').val();
    if (["pes", "magnus", "corail"].indexOf(format) === -1) {return;}
    var actif = $(this).prop("checked");
    $('#div_id_modele_document, #div_id_type_pj').toggle(actif);
    // PES : la balise Edition impose de joindre les factures
    if (format === "pes") {
        $('#div_id_edition_asap').toggle(actif);
        if (!actif) {$('#id_edition_asap').val("");}
    }
}
$(document).ready(function() {
    $('#id_inclure_pieces_jointes').change(On_change_inclure_pieces_jointes);
    On_change_inclure_pieces_jointes.call($('#id_inclure_pieces_jointes').get(0));
});

</script>
"""
