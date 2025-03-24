# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, HTML, Fieldset
from crispy_forms.bootstrap import Field
from core.utils.utils_commandes import Commandes
from core.models import PesLot, PesModele, PesPiece, Rattachement, Mandat, LotFactures, FiltreListe, Facture, LISTE_MOIS
from core.widgets import DatePickerWidget
from core.forms.base import FormulaireBase


class Formulaire_creation(FormulaireBase, forms.Form):
    modele = forms.ModelChoiceField(label="Modèle d'export", queryset=PesModele.objects.all().order_by("nom"), required=True, help_text="Sélectionnez obligatoirement un modèle d'export dans la liste proposée. Vous pouvez les créer depuis le menu Paramétrage > Modèles > Modèles d'export vers le Trésor Public.")
    assistant = forms.ChoiceField(label="Génération automatique des pièces", choices=[], initial=0, required=False, help_text="Vous pouvez sélectionner des factures à insérer automatiquement dans l'export [Optionnel]. A défaut, vous pourrez les sélectionner vous-même dans la liste des factures.")

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop("instance", None)
        super(Formulaire_creation, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'

        # Assistant de préparation
        lots_factures = LotFactures.objects.order_by("-pk")
        liste_choix = [(0, "Aucune")]
        if FiltreListe.objects.filter(nom="facturation.views.lots_pes_factures", parametres__contains="Dernières factures générées", utilisateur=self.request.user):
            liste_choix += [(999999, "Les dernières factures générées")]
            self.fields["assistant"].initial = 999999

            # Recherche un modèle d'export dont le nom ressemble au nom du lot de factures
            derniere_facture = Facture.objects.last()
            if derniere_facture and derniere_facture.lot:
                nom_lot = derniere_facture.lot.nom
                import jellyfish
                scores = []
                for modele in PesModele.objects.all():
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
        model = PesLot
        fields = "__all__"
        widgets = {
            "date_emission": DatePickerWidget(attrs={"afficher_fleches": True}),
            "date_prelevement": DatePickerWidget(attrs={"afficher_fleches": True}),
            "date_envoi": DatePickerWidget(attrs={"afficher_fleches": True}),
            "observations": forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        idmodele = kwargs.pop("idmodele", None)
        assistant = kwargs.pop("assistant", None)
        if kwargs.get("instance", None):
            idmodele = kwargs["instance"].modele_id
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'lots_pes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Modèle d'export
        self.fields["modele"].disabled = True
        modele = PesModele.objects.get(pk=idmodele)

        # Valeurs par défaut si ajout
        if not self.instance.pk:
            self.fields["modele"].initial = modele
            self.fields["exercice"].initial = datetime.date.today().year
            self.fields["mois"].initial = datetime.date.today().month
            self.fields["date_emission"].initial = datetime.date.today()
            self.fields["date_prelevement"].initial = datetime.date.today()
            self.fields["date_envoi"].initial = datetime.date.today()

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

            # Essaye de deviner l'exercice et le mois selon le nom de l'export
            nom_lot = self.fields["nom"].initial
            if nom_lot:
                for num_mois, nom_mois in LISTE_MOIS:
                    if nom_mois.lower() in nom_lot.lower():
                        self.fields["mois"].initial = num_mois
                for annee in [datetime.date.today().year-1, datetime.date.today().year, datetime.date.today().year+1]:
                    if str(annee) in nom_lot:
                        self.fields["exercice"].initial = annee

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'lots_pes_liste' %}", ajouter=False),
            Fieldset("Généralités",
                Field("modele"),
                Field("nom"),
                Field("observations"),
            ),
            Fieldset("Paramètres",
                Field("exercice"),
                Field("mois"),
                Field("date_emission"),
                Field("date_prelevement"),
                Field("date_envoi"),
                Field("id_bordereau", type=None if modele.format in ("pes", "jvs") else "hidden"),
            ),
        )

    def clean(self):
        format = self.cleaned_data["modele"].format

        if not self.cleaned_data["id_bordereau"] and format in ("pes", "jvs"):
            self.add_error("id_bordereau", "Vous devez renseigner l'identifiant du bordereau")

        return self.cleaned_data


class Formulaire_piece(FormulaireBase, ModelForm):
    famille = forms.CharField(label="Texte", required=False)

    class Meta:
        model = PesPiece
        fields = ["prelevement", "prelevement_mandat", "prelevement_sequence", "prelevement_statut", "titulaire_helios", "tiers_solidaire", "type", "montant"]

    def __init__(self, *args, **kwargs):
        super(Formulaire_piece, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'piece_pes_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Désactive certains champs
        for champ in ("type", "montant"):
            self.fields[champ].disabled = True

        # Titulaire hélios et tiers solidaire
        rattachements = Rattachement.objects.select_related("individu").filter(famille=self.instance.famille, titulaire=True).order_by("individu__nom", "individu__prenom")
        self.fields["titulaire_helios"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]
        self.fields["tiers_solidaire"].choices = [(None, "---------")] + [(rattachement.individu.idindividu, rattachement.individu) for rattachement in rattachements]

        # Mandat
        self.fields["prelevement_mandat"].choices = [(None, "---------")] + [(mandat.pk, mandat.rum) for mandat in Mandat.objects.filter(famille=self.instance.famille)]

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{% url 'lots_pes_consulter' pk=" + str(self.instance.lot_id) + " %}", ajouter=False),
            HTML(EXTRA_HTML),
            Fieldset("Pièce",
                Field("type"),
                Field("montant"),
            ),
            Fieldset("Prélèvement",
                Field("prelevement"),
                Field("prelevement_mandat"),
                Field("prelevement_sequence"),
                Field("prelevement_statut"),
            ),
            Fieldset("Options",
                Field("titulaire_helios"),
                Field("tiers_solidaire"),
            ),
        )

EXTRA_HTML = """
<div class="info-box bg-light">
    <div class="info-box-content">
        <span class="info-box-number text-center text-muted mb-0">{{ object.famille.nom }}</span>
        <span class="info-box-text text-center text-muted mb-0">{{ object.get_type_display }} n°{{ object.facture.numero }} - {{ object.montant|montant }}</span>
    </div>
</div>
"""