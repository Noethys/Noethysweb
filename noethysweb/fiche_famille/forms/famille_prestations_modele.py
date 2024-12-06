# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, decimal, json
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


LISTE_CHOIX_MULTI_PRESTATIONS = [
    (None, "Non"),
    ("REPARTITION_MENSUELLE_X_MOIS", "Répartir le montant en plusieurs prestations sur x mois"),
    ("REPARTITION_MENSUELLE_DATES", "Répartir le montant sur une sélection de dates"),
    ("MULTIPLICATION_MENSUELLE_X_MOIS", "Générer plusieurs prestations identiques sur x mois"),
    ("MULTIPLICATION_MENSUELLE_DATES", "Générer plusieurs prestations identiques sur une sélection de dates"),
]


class Widget_modele(ModelSelect2Widget):
    search_fields = ["label__icontains"]

    def label_from_instance(widget, instance):
        return instance.label


class Formulaire(FormulaireBase, ModelForm):
    multiprestations = forms.ChoiceField(label="Multi-prestations", initial=None, required=False, choices=LISTE_CHOIX_MULTI_PRESTATIONS, help_text="Cette option permet de générer plusieurs prestations selon le même modèle.")
    nbre_mois = forms.IntegerField(label="Nbre mois", initial=1, min_value=1, required=False, help_text="Une prestation sera générée pour chaque mois à partir de la date saisie ci-dessus.")
    selection_dates = forms.CharField(label="Dates", widget=forms.Textarea(attrs={"rows": 2}), required=False, help_text="Saisissez les dates souhaitées pour chaque prestation (séparées par des points-virgules). Exemple : 01/01/2024;01/02/2024;15/03/2024...")

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
            montant_found = False
            for ligne in modele.tarifs.splitlines():
                tranches, montant_tarif = ligne.split("=")
                qf_min, qf_max = tranches.split("-")
                liste_montants.append(float(montant_tarif))
                if qf_famille and float(qf_min) <= qf_famille.quotient <= float(qf_max):
                    montant = float(montant_tarif)
                    montant_found = True
            if not qf_famille or not montant_found:
                montant = max(liste_montants)

        self.fields["montant"].initial = montant
        montant_initial = montant if not modele.tva else round(montant / (1 + modele.tva / decimal.Decimal(100.0)), 2)

        # Date de la prestation
        self.fields["date"].initial = datetime.date.today()

        # Individu
        rattachements = Rattachement.objects.select_related("individu").filter(famille_id=idfamille).order_by("individu__nom", "individu__prenom")
        self.fields["individu"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]
        if modele.public == "individu":
            self.fields["individu"].required = True

        # Multiprestations
        if modele.multiprestations:
            dict_parametres = json.loads(modele.multiprestations)
            for key, valeur in dict_parametres.items():
                self.fields[key].initial = valeur

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}", ajouter=False),
            Hidden("famille", value=idfamille),
            Hidden("categorie", value=modele.categorie),
            Hidden("montant_initial", value=montant_initial),
            Hidden("tva", value=modele.tva),
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
                Field("selection_dates"),
            ),
            HTML(EXTRA_HTML),
        )

        # Ajout d'autres champs du modèle
        for champ in ("activite_id", "categorie_tarif_id", "tarif_id", "code_compta"):
            valeur = getattr(modele, champ)
            if valeur:
                self.helper.layout.append(Hidden(champ.replace("_id", ""), value=valeur))

    def clean(self):
        if self.cleaned_data["multiprestations"] in ("REPARTITION_MENSUELLE_X_MOIS", "MULTIPLICATION_MENSUELLE_X_MOIS") and not self.cleaned_data["nbre_mois"]:
            self.add_error("nbre_mois", "Vous devez saisir un nombre de mois")
            return
        if self.cleaned_data["multiprestations"] in ("REPARTITION_MENSUELLE_DATES", "MULTIPLICATION_MENSUELLE_DATES"):
            try:
                for date in self.cleaned_data["selection_dates"].split(";"):
                    date_temp = datetime.datetime.strptime(date.strip(), "%d/%m/%Y").date()
            except:
                self.add_error("selection_dates", "Vous devez saisir au moins une date valide")
                return
        return self.cleaned_data


EXTRA_HTML = """
<script>
    function On_change_multiprestations() {
        $('#div_id_nbre_mois').hide();
        $('#div_id_selection_dates').hide();
        if ($("#id_multiprestations").val() == 'REPARTITION_MENSUELLE_X_MOIS') {
            $('#div_id_nbre_mois').show();
        };
        if ($("#id_multiprestations").val() == 'REPARTITION_MENSUELLE_DATES') {
            $('#div_id_selection_dates').show();
        };
        if ($("#id_multiprestations").val() == 'MULTIPLICATION_MENSUELLE_X_MOIS') {
            $('#div_id_nbre_mois').show();
        };
        if ($("#id_multiprestations").val() == 'MULTIPLICATION_MENSUELLE_DATES') {
            $('#div_id_selection_dates').show();
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
