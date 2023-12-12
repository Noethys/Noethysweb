# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.utils.translation import gettext_lazy as _
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from core.models import Individu, Rattachement
from core.forms.select2 import Select2Widget
from core.widgets import Telephone, CodePostal, Ville
from portail.forms.fiche import FormulaireBase


class Formulaire(FormulaireBase, ModelForm):
    type_adresse = forms.ChoiceField(label=_("Type d'adresse"), widget=forms.RadioSelect, choices=[("RATTACHEE", _("Adresse rattachée")), ("PROPRE", _("Adresse propre"))], required=False)
    adresse_auto = forms.ModelChoiceField(label=_("Adresse rattachée"), widget=Select2Widget(), queryset=Rattachement.objects.none(), required=False)

    class Meta:
        model = Individu
        fields = [
            "adresse_auto", "rue_resid", "cp_resid", "ville_resid", "secteur",
            "tel_domicile","tel_mobile", "mail",
            "categorie_travail","profession", "employeur", "travail_tel", "travail_mail",
            "tel_domicile_sms","tel_mobile_sms", "travail_tel_sms", #"listes_diffusion",
        ]
        widgets = {
            'tel_domicile': Telephone(),
            'tel_mobile': Telephone(),
            'tel_fax': Telephone(),
            'travail_tel': Telephone(),
            'travail_fax': Telephone(),
            'rue_resid': forms.Textarea(attrs={'rows': 2}),
            'cp_resid': CodePostal(attrs={"id_ville": "id_ville_resid"}),
            'ville_resid': Ville(attrs={"id_codepostal": "id_cp_resid"}),
        }

    def __init__(self, *args, **kwargs):
        self.rattachement = kwargs.pop("rattachement", None)
        self.mode = kwargs.pop("mode", "CONSULTATION")
        self.nom_page = "individu_coords"
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_coords_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'
        self.helper.use_custom_control = False

        # Adresse rattachée
        individus = []
        for rattachement in Rattachement.objects.select_related('individu').filter(famille=self.rattachement.famille).exclude(individu=self.instance):
            if rattachement.individu.adresse_auto == None:
                individus.append(rattachement.individu_id)
        self.fields['adresse_auto'].queryset = Individu.objects.filter(pk__in=individus).order_by("nom")

        if self.instance.adresse_auto != None:
            self.fields['type_adresse'].initial = "RATTACHEE"
        else:
            self.fields['type_adresse'].initial = "PROPRE"

        # Help_texts pour le mode édition
        self.help_texts = {
            "type_adresse": _("Sélectionnez 'rattachée' pour faire le lien avec l'adresse d'un autre membre de la famille ou sélectionnez 'propre' pour saisir une adresse pour cet individu."),
            "adresse_auto": _("Sélectionnez l'individu dont vous souhaitez récupérer l'adresse."),
            "rue_resid": _("Saisissez le numéro et le nom de la voie. Exemple : 12 Rue des acacias."),
            "cp_resid": _("Saisissez le code postal de la ville de résidence, attendez une seconde et sélectionnez la ville dans la liste déroulante."),
            "ville_resid": _("Saisissez le nom de la ville en majuscules."),
            "secteur": _("Sélectionnez un secteur dans la liste déroulante."),
            "tel_domicile": _("Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx."),
            "tel_mobile": _("Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx."),
            "mail": _("Saisissez une adresse Email valide."),
            "categorie_travail": _("Sélectionnez une catégorie socio-professionnelle dans la liste déroulante."),
            "profession": _("Saisissez une profession."),
            "employeur": _("Saisissez le nom de l'employeur."),
            "travail_tel": _("Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx."),
            "travail_mail": _("Saisissez une adresse Email valide."),
        }

        # Champs affichables
        self.liste_champs_possibles = [
            {"titre": _("Adresse de résidence"), "champs": ["type_adresse", "adresse_auto", "rue_resid", "cp_resid", "ville_resid", "secteur"]},
            {"titre": _("Coordonnées"), "champs": ["tel_domicile", "tel_mobile", "mail"]},
            {"titre": _("Activité professionnelle"), "champs": ["categorie_travail", "profession", "employeur", "travail_tel", "travail_mail"]},
        ]

        # Finalisation du layout
        self.Set_layout()
        self.helper.layout.append(HTML(EXTRA_SCRIPT))

    def clean(self):
        # Adresse auto
        if self.cleaned_data["type_adresse"] == "PROPRE":
            self.cleaned_data["adresse_auto"] = None

        if self.cleaned_data["type_adresse"] == "RATTACHEE":
            if self.cleaned_data["adresse_auto"]:
                individu = self.cleaned_data["adresse_auto"]
                self.cleaned_data["adresse_auto"] = individu.idindividu
            else:
                self.add_error("adresse_auto", _("Vous devez sélectionner un individu dont l'adresse est à rattacher"))
                return

        return self.cleaned_data


EXTRA_SCRIPT = """

<script>

// type adresse
function On_change_type_adresse() {
    $('#div_id_adresse_auto').hide();
    $('#div_id_rue_resid').hide();
    $('#div_id_cp_resid').hide();
    $('#div_id_ville_resid').hide();
    $('#div_id_secteur').hide();
    if ($(this).prop("checked") && this.value == 'RATTACHEE') {
        $('#div_id_adresse_auto').show();
    };
    if ($(this).prop("checked") && this.value == 'PROPRE') {
        $('#div_id_rue_resid').show();
        $('#div_id_cp_resid').show();
        $('#div_id_ville_resid').show();
        $('#div_id_secteur').show();
    };
    if ($(this).prop("checked") == false && this.value == 'RATTACHEE') {
        $('#div_id_rue_resid').show();
        $('#div_id_cp_resid').show();
        $('#div_id_ville_resid').show();
        $('#div_id_secteur').show();
    };
}
$(document).ready(function() {
    $('input[type=radio][name=type_adresse]').on('change', On_change_type_adresse);
    On_change_type_adresse.call($('input[type=radio][name=type_adresse]').get(0));
});

</script>
"""
