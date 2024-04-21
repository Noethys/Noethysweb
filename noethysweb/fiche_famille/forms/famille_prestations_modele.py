# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from django.db.models import Q
from django_select2.forms import ModelSelect2Widget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Submit, HTML, Fieldset, ButtonHolder
from crispy_forms.bootstrap import Field, PrependedText
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences
from core.models import Rattachement, Prestation, ModelePrestation, Quotient
from core.widgets import DatePickerWidget


class Widget_modele(ModelSelect2Widget):
    search_fields = ["label__icontains"]

    def label_from_instance(widget, instance):
        return instance.label


class Formulaire(FormulaireBase, ModelForm):
    multiprestations = forms.ChoiceField(label="Multi-prestations", choices=[(None, "Non"), ("REPARTITION_MENSUELLE", "Répartir le montant en plusieurs prestations sur x mois"), ("MULTIPLICATION_MENSUELLE", "Générer plusieurs prestations identiques sur x mois")], initial=None, required=False, help_text="Cette option permet de générer plusieurs prestations selon le même modèle.")
    nbre_mois = forms.IntegerField(label="Nbre mois", initial=1, min_value=1, required=False, help_text="Une prestation sera générée pour chaque mois à partir de la date saisie ci-dessus.")

    class Meta:
        model = Prestation
        fields = "__all__"
        widgets = {
            "date": DatePickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        idmodele = kwargs.pop("idmodele")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_prestations_modele_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3 col-form-label'
        self.helper.field_class = 'col-md-9'

        # Importe le modèle de prestation
        modele = ModelePrestation.objects.get(pk=idmodele)

        # Calcul du montant
        montant = modele.montant
        if modele.tarifs:
            qf_famille = Quotient.objects.filter(famille_id=idfamille, date_debut__lte=datetime.date.today(), date_fin__gte=datetime.date.today()).first()
            liste_montants = []
            for ligne in modele.tarifs.splitlines():
                tranches, montant_tarif = ligne.split("=")
                qf_min, qf_max = tranches.split("-")
                liste_montants.append(float(montant_tarif))
                if qf_famille and float(qf_min) <= qf_famille.quotient <= float(qf_max):
                    montant = float(montant_tarif)
            if not qf_famille:
                montant = max(liste_montants)

        self.fields["montant"].initial = montant
        montant_initial = montant

        # Date de la prestation
        self.fields["date"].initial = datetime.date.today()

        # Individu
        rattachements = Rattachement.objects.select_related("individu").filter(famille_id=idfamille).order_by("individu__nom", "individu__prenom")
        self.fields["individu"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]
        if modele.public == "individu":
            self.fields["individu"].required = True

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}", ajouter=False),
            Hidden("famille", value=idfamille),
            Hidden("categorie", value=modele.categorie),
            Hidden("montant_initial", value=montant_initial),
            Hidden("quantite", value=1),
            Fieldset("Généralités",
                Field("date"),
                Field("label", value=modele.label),
                Field("individu", type=None if modele.public == "individu" else "hidden"),
                PrependedText("montant", utils_preferences.Get_symbole_monnaie()),
            ),
            Fieldset("Options",
                Field("multiprestations"),
                Field("nbre_mois"),
            ),
            HTML(EXTRA_HTML),
        )

    def clean(self):
        if self.cleaned_data["multiprestations"] in ("REPARTITION_MENSUELLE", "MULTIPLICATION_MENSUELLE") and not self.cleaned_data["nbre_mois"]:
            self.add_error("nbre_mois", "Vous devez saisir un nombre de mois")
            return
        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_multiprestations() {
        $('#div_id_nbre_mois').hide();
        if ($("#id_multiprestations").val() == 'REPARTITION_MENSUELLE') {
            $('#div_id_nbre_mois').show();
        };
        if ($("#id_multiprestations").val() == 'MULTIPLICATION_MENSUELLE') {
            $('#div_id_nbre_mois').show();
        };
    }
    $(document).ready(function() {
        $('#id_multiprestations').on('change', On_change_multiprestations);
        On_change_multiprestations.call($('#id_multiprestations').get(0));
    });
</script>
"""


class Formulaire_selection_modele(FormulaireBase, forms.Form):
    modele = forms.ModelChoiceField(label="Modèle", widget=Widget_modele({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}), queryset=ModelePrestation.objects.none(), required=True)

    def __init__(self, *args, **kwargs):
        super(Formulaire_selection_modele, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Liste les
        condition_structure = (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        self.fields["modele"].queryset = ModelePrestation.objects.filter(condition_structure).order_by("label")

        self.helper.layout = Layout(
            Field('modele'),
            ButtonHolder(
                Submit('submit', 'Valider', css_class='btn-primary'),
                HTML("""<a class="btn btn-danger" href="{{ view.Get_annuler_url }}"><i class='fa fa-ban margin-r-5'></i>Annuler</a>"""),
                css_class="pull-right",
            )
        )
