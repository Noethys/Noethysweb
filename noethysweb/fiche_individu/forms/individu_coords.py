# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django import forms
from django.forms import ModelForm
from core.forms.base import FormulaireBase
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, Div, ButtonHolder
from crispy_forms.bootstrap import Field, InlineRadios
from core.utils.utils_commandes import Commandes
from core.models import Individu, ListeDiffusion, Rattachement
from core.forms.select2 import Select2MultipleWidget, Select2Widget
from core.widgets import Telephone, CodePostal, Ville
from fiche_individu.widgets import CarteOSM


class Formulaire(FormulaireBase, ModelForm):
    type_adresse = forms.ChoiceField(label="Type d'adresse", widget=forms.RadioSelect, choices=[("RATTACHEE", "Adresse rattachée"), ("PROPRE", "Adresse propre")], required=False)
    adresse_auto = forms.ModelChoiceField(label="Adresse rattachée", widget=Select2Widget(), queryset=Rattachement.objects.none(), required=False)
    listes_diffusion = forms.ModelMultipleChoiceField(label="Listes de diffusion", widget=Select2MultipleWidget(), queryset=ListeDiffusion.objects.all(), required=False)
    carte = forms.ChoiceField(label="Localisation", widget=CarteOSM(), required=False)

    class Meta:
        model = Individu
        fields = [
            "adresse_auto", "rue_resid", "cp_resid", "ville_resid", "secteur",
            "tel_domicile","tel_mobile", "tel_fax", "mail",
            "categorie_travail","profession", "employeur", "travail_tel", "travail_fax", "travail_mail",
            "tel_domicile_sms","tel_mobile_sms", "travail_tel_sms", "listes_diffusion",
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
        help_texts = {
            "type_adresse": "Sélectionnez 'rattachée' pour faire le lien avec l'adresse d'un autre membre de la famille ou sélectionnez 'propre' pour saisir une adresse pour cet individu.",
            "adresse_auto": "Sélectionnez l'individu dont vous souhaitez récupérer l'adresse.",
            "rue_resid": "Saisissez le numéro et le nom de la voie. Exemple : 12 Rue des acacias.",
            "cp_resid": "Saisissez le code postal de la ville de résidence, attendez une seconde et sélectionnez la ville dans la liste déroulante.",
            "ville_resid": "Saisissez le nom de la ville en majuscules.",
            "secteur": "Sélectionnez un secteur dans la liste déroulante.",
            "tel_domicile": "Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx.",
            "tel_mobile": "Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx.",
            "mail": "Saisissez une adresse Email valide.",
            "categorie_travail": "Sélectionnez une catégorie socio-professionnelle dans la liste déroulante.",
            "profession": "Saisissez une profession.",
            "employeur": "Saisissez le nom de l'employeur.",
            "travail_tel": "Saisissez un numéro de téléphone au format xx.xx.xx.xx.xx.",
            "travail_mail": "Saisissez une adresse Email valide.",
        }


    def __init__(self, *args, **kwargs):
        self.idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'individu_coords_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2 col-form-label'
        self.helper.field_class = 'col-md-10'

        # Adresse rattachée
        individus = []
        for rattachement in Rattachement.objects.select_related('individu').filter(famille_id=self.idfamille).exclude(individu=self.instance):
            if rattachement.individu.adresse_auto == None:
                individus.append(rattachement.individu_id)
        self.fields['adresse_auto'].queryset = Individu.objects.filter(pk__in=individus).order_by("nom")

        if self.instance.adresse_auto != None:
            self.fields['type_adresse'].initial = "RATTACHEE"
        else:
            self.fields['type_adresse'].initial = "PROPRE"

        # Création des boutons de commande
        if self.mode == "CONSULTATION":
            commandes = Commandes(modifier_url="individu_coords_modifier", modifier_args="idfamille=idfamille idindividu=idindividu",
                                  modifier=self.request.user.has_perm("core.individu_coords_modifier"), enregistrer=False, annuler=False, ajouter=False)
            self.Set_mode_consultation()
        else:
            commandes = Commandes(annuler_url="{% url 'individu_coords' idfamille=idfamille idindividu=idindividu %}", ajouter=False)

        # Affichage
        self.helper.layout = Layout(
            commandes,
            Fieldset("Adresse de résidence",
                InlineRadios("type_adresse"),
                Field("adresse_auto"),
                Div(
                    Field("rue_resid"),
                    Field("cp_resid"),
                    Field("ville_resid"),
                    Field("secteur"),
                    id="adresse_propre",
                ),
                Field("carte"),
            ),
            Fieldset("Coordonnées",
                Field("tel_domicile"),
                Field("tel_mobile"),
                Field("tel_fax"),
                Field("mail"),
            ),
            Fieldset("Activité professionnelle",
                Field("categorie_travail"),
                Field("profession"),
                Field("employeur"),
                Field("travail_tel"),
                Field("travail_fax"),
                Field("travail_mail"),
            ),
            Fieldset("Envoi de SMS",
                Field("tel_domicile_sms"),
                Field("tel_mobile_sms"),
                Field("travail_tel_sms"),
            ),
            Fieldset("Listes de diffusion",
                Field("listes_diffusion"),
            ),
            HTML(EXTRA_SCRIPT),
        )

    def clean(self):
        # Adresse auto
        if self.cleaned_data["type_adresse"] == "PROPRE":
            self.cleaned_data["adresse_auto"] = None

        if self.cleaned_data["type_adresse"] == "RATTACHEE":
            if self.cleaned_data["adresse_auto"]:
                individu = self.cleaned_data["adresse_auto"]
                self.cleaned_data["adresse_auto"] = individu.idindividu
            else:
                self.add_error("adresse_auto", "Vous devez sélectionner un individu dont l'adresse est à rattacher")
                return

        return self.cleaned_data


EXTRA_SCRIPT = """

<script>

// type adresse
function On_change_type_adresse() {
    $('#div_id_adresse_auto').hide();
    $('#adresse_propre').hide();
    if ($(this).prop("checked") && this.value == 'RATTACHEE') {
        $('#div_id_adresse_auto').show();
    };
    if ($(this).prop("checked") && this.value == 'PROPRE') {
        $('#adresse_propre').show();
    };
    if ($(this).prop("checked") == false && this.value == 'RATTACHEE') {
        $('#adresse_propre').show();
    };
}
$(document).ready(function() {
    $('input[type=radio][name=type_adresse]').on('change', On_change_type_adresse);
    On_change_type_adresse.call($('input[type=radio][name=type_adresse]').get(0));
});

</script>
"""