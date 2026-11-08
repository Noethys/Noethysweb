# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import Famille, Rattachement
from core.forms.base import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):
    mail = forms.ChoiceField(label="Mail favori", choices=[], required=False, help_text="Adresse utilisée en priorité pour tous les e-mails envoyés à la famille (factures, reçus, courriers...).")
    mobile = forms.ChoiceField(label="Portable favori", choices=[], required=False, help_text="Numéro utilisé en priorité pour tous les SMS envoyés à la famille.")

    class Meta:
        model = Famille
        fields = ["mail", "mobile", "memo", "code_compta", "titulaire_helios", "tiers_solidaire", "idtiers_helios", "natidtiers_helios", "reftiers_helios",
                  "cattiers_helios", "natjur_helios", "facturation_nom", "facturation_rue_resid", "facturation_cp_resid", "facturation_ville_resid",
                  "email_blocage", "mobile_blocage"]
        widgets = {
            "memo": forms.Textarea(attrs={'rows': 3}),
            "facturation_rue_resid": forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            "memo": "Note libre affichée sur la fiche famille.",
            "email_blocage": "Cochez pour que la famille ne soit pas proposée comme destinataire dans les envois d'e-mails groupés du menu Outils.",
            "mobile_blocage": "Cochez pour que la famille ne soit pas proposée comme destinataire dans les envois de SMS groupés du menu Outils.",
            "code_compta": "Code de la famille dans votre logiciel de comptabilité, repris dans les exports comptables.",
            "titulaire_helios": "Membre de la famille déclaré comme débiteur dans les exports vers Hélios (Trésor public).",
            "tiers_solidaire": "Second responsable déclaré comme tiers solidaire dans les exports vers Hélios.",
            "idtiers_helios": "Identifiant national du tiers (SIRET, SIREN, FINESS ou NIR), si l'export Hélios l'exige.",
            "natidtiers_helios": "Type de l'identifiant national saisi ci-dessus.",
            "reftiers_helios": "Référence du tiers dans votre propre système, si vous en utilisez une.",
            "cattiers_helios": "Catégorie du tiers pour les exports vers Hélios.",
            "natjur_helios": "Nature juridique du tiers pour les exports vers Hélios.",
            "facturation_nom": "Facultatif : nom à imprimer sur les factures à la place du nom de la famille.",
            "facturation_rue_resid": "Facultatif : adresse à imprimer sur les factures à la place de l'adresse de la famille.",
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_divers_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        rattachements = Rattachement.objects.select_related("individu").filter(famille_id=idfamille, titulaire=True).order_by("individu__nom", "individu__prenom")

        # Coordonnées favorites
        self.fields["mail"].choices = [(None, "---------")] + [(rattachement.individu.mail, rattachement.individu.mail) for rattachement in rattachements if rattachement.individu.mail]
        self.fields["mobile"].choices = [(None, "---------")] + [(rattachement.individu.tel_mobile, "%s (%s)" % (rattachement.individu.tel_mobile, rattachement.individu.Get_nom())) for rattachement in rattachements if rattachement.individu.tel_mobile]

        # Titulaire hélios
        self.fields["titulaire_helios"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]
        self.fields["tiers_solidaire"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="famille_divers_modifier", modifier_args="idfamille=idfamille",
                                  modifier=self.request.user.has_perm("core.famille_divers_modifier"), enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'famille_divers' idfamille=idfamille %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Fieldset("Mémo",
                Field("memo"),
            ),
            Fieldset("Coordonnées",
                Field("mail"),
                Field("email_blocage"),
                Field("mobile"),
                Field("mobile_blocage"),
            ),
            Fieldset("Comptabilité",
                Field("code_compta"),
            ),
            Fieldset("Données tiers pour Hélios",
                Field("titulaire_helios"),
                Field("tiers_solidaire"),
                Field("idtiers_helios"),
                Field("natidtiers_helios"),
                Field("reftiers_helios"),
                Field("cattiers_helios"),
                Field("natjur_helios"),
            ),
            Fieldset("Autre adresse de facturation",
                Field("facturation_nom"),
                Field("facturation_rue_resid"),
                Field("facturation_cp_resid"),
                Field("facturation_ville_resid"),
            ),
        )

    def clean(self):
        return self.cleaned_data
