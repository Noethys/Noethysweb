# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field, PrependedText
from django_select2.forms import Select2Widget
from core.utils.utils_commandes import Commandes
from core.utils import utils_preferences
from core.models import PrelevementsLot, PrelevementsModele, Prelevements, Mandat, LotFactures, FiltreListe, Facture, Famille
from core.widgets import DatePickerWidget
from core.forms.base import FormulaireBase


class Formulaire_creation(FormulaireBase, forms.Form):
    modele = forms.ModelChoiceField(label="Modèle", queryset=PrelevementsModele.objects.all().order_by("nom"), required=True, help_text="Sélectionnez obligatoirement un modèle dans la liste proposée. Vous pouvez les créer depuis le menu Paramétrage > Modèles > Modèles de prélèvements.")
    assistant = forms.ChoiceField(label="Génération automatique des pièces", choices=[], initial=0, required=False, help_text="Vous pouvez sélectionner des factures à insérer automatiquement dans le lot [Optionnel]. A défaut, vous pourrez les sélectionner vous-même dans la liste des factures.")

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Assistant de préparation
        lots_factures = LotFactures.objects.order_by("-pk")
        liste_choix = [(0, "Aucune")]
        if FiltreListe.objects.filter(nom="facturation.views.lots_prelevements_factures", parametres__contains="Dernières factures générées", utilisateur=self.request.user):
            liste_choix += [(999999, "Les dernières factures générées")]
            self.fields["assistant"].initial = 999999

            # Recherche un modèle dont le nom ressemble au nom du lot de factures
            derniere_facture = Facture.objects.last()
            if derniere_facture:
                nom_lot = derniere_facture.lot.nom
                import jellyfish
                scores = []
                for modele in PrelevementsModele.objects.all():
                    try:
                        distance = jellyfish.jaro_distance(modele.nom.lower(), nom_lot.lower())
                    except:
                        distance = jellyfish.jaro_similarity(modele.nom.lower(), nom_lot.lower())
                    scores.append((distance, modele))
                if scores:
                    self.fields["modele"].initial = max(scores)[1]

        self.fields["assistant"].choices = liste_choix + [(lot.pk, "Le lot de factures %s" % lot.nom) for lot in lots_factures]

        self.helper.layout = Layout(
            Commandes(enregistrer_label="<i class='fa fa-check margin-r-5'></i>Valider", ajouter=False, annuler_url="{{ view.get_success_url }}"),
            Fieldset("Paramètres de création",
                Field("modele"),
                Field("assistant"),
            ),
        )


class Formulaire(FormulaireBase, ModelForm):

    class Meta:
        model = PrelevementsLot
        fields = "__all__"
        widgets = {
            "date": DatePickerWidget(attrs={"afficher_fleches": True}),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        idmodele = kwargs.pop("idmodele", None)
        assistant = kwargs.pop("assistant", None)
        if kwargs.get("instance", None):
            idmodele = kwargs["instance"].modele_id
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'lots_prelevements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Modèle
        self.fields["modele"].disabled = True
        modele = PrelevementsModele.objects.get(pk=idmodele)

        # Valeurs par défaut si ajout
        if not self.instance.pk:
            self.fields["modele"].initial = modele
            self.fields["date"].initial = datetime.date.today()

            # Importe le nom de lot de factures pour l'utiliser comme nom de lot pes
            if assistant and assistant > 0:
                premiere_facture = None
                if assistant == 999999:
                    filtre = FiltreListe.objects.filter(nom="facturation.views.lots_pes_factures", parametres__contains="Dernières factures générées", utilisateur=self.request.user).first()
                    if filtre:
                        parametres_filtre = json.loads(filtre.parametres)
                        idmin, idmax = parametres_filtre["criteres"]
                        premiere_facture = Facture.objects.select_related("lot").filter(pk__gte=idmin, pk__lte=idmax).first()
                else:
                    premiere_facture = Facture.objects.select_related("lot").filter(lot_id=assistant).first()
                if premiere_facture and premiere_facture.lot:
                    self.fields["nom"].initial = premiere_facture.lot.nom

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'lots_prelevements_liste' %}", ajouter=False),
            Fieldset("Généralités",
                Field("modele"),
                Field("nom"),
                Field("observations"),
            ),
            Fieldset("Paramètres",
                Field("date"),
                Field("motif"),
                Field("numero_sequence", type=None if modele.format in ("public_dft",) else "hidden"),
            ),
        )

    def clean(self):
        format = self.cleaned_data["modele"].format

        if not self.cleaned_data["motif"] and format in ("prive", "public_dft"):
            self.add_error("motif", "Vous devez renseigner le motif")

        if not self.cleaned_data["numero_sequence"] and format in ("public_dft",):
            self.add_error("numero_sequence", "Vous devez renseigner le numéro de séquence")

        return self.cleaned_data


class Formulaire_piece(FormulaireBase, ModelForm):
    famille = forms.CharField(label="Texte", required=False)

    class Meta:
        model = Prelevements
        fields = ["mandat", "sequence", "statut", "type", "montant", "libelle"]

    def __init__(self, *args, **kwargs):
        super(Formulaire_piece, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'piece_prelevements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Désactive certains champs
        self.fields["type"].disabled = True
        self.fields["montant"].disabled = True
        if self.instance.type != "manuel":
            self.fields["libelle"].disabled = True

        # Mandat
        self.fields["mandat"].choices = [(None, "---------")] + [(mandat.pk, mandat.rum) for mandat in Mandat.objects.filter(famille=self.instance.famille)]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'lots_prelevements_consulter' pk=" + str(self.instance.lot_id) + " %}", ajouter=False),
            HTML(EXTRA_HTML),
            Fieldset("Pièce",
                Field("type"),
                Field("montant"),
                Field("libelle"),
            ),
            Fieldset("Prélèvement",
                Field("mandat"),
                Field("sequence"),
                Field("statut"),
            ),
        )

EXTRA_HTML = """
<div class="info-box bg-light">
    <div class="info-box-content">
        <span class="info-box-number text-center text-muted mb-0">{{ object.famille.nom }}</span>
        <span class="info-box-text text-center text-muted mb-0">{% if object.facture %}{{ object.get_type_display }} n°{{ object.facture.numero }}{% else %}Prélèvement manuel{% endif %} - {{ object.montant|montant }}</span>
    </div>
</div>
"""


class Formulaire_piece_manuelle(FormulaireBase, ModelForm):
    famille = forms.ModelChoiceField(label="Famille", widget=Select2Widget({"lang": "fr", "data-width": "100%", "data-minimum-input-length": 0}),
                                     queryset=Famille.objects.all().order_by("nom"), required=True)
    libelle = forms.CharField(label="Libellé", required=True)

    class Meta:
        model = Prelevements
        fields = ["famille", "montant", "libelle"]

    def __init__(self, *args, **kwargs):
        idlot = kwargs.pop("idlot", None)
        super(Formulaire_piece_manuelle, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'piece_manuelle_prelevements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'lots_prelevements_consulter' pk=" + str(idlot) + " %}", ajouter=False),
            Field("famille"),
            Field("libelle"),
            PrependedText("montant", utils_preferences.Get_symbole_monnaie()),
        )
