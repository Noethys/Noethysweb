# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from django import forms
from django.forms import ModelForm, HiddenInput, ValidationError
from django.forms.models import inlineformset_factory, BaseInlineFormSet, model_to_dict
from django.core.validators import MinValueValidator
from django.utils.dateparse import parse_time, parse_date
from django.utils.safestring import mark_safe
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset, Div
from crispy_forms.bootstrap import Field, PrependedText, TabHolder, Tab, InlineCheckboxes
from core.forms.base import FormulaireBase
from core.forms.select2 import Select2MultipleWidget
from core.utils.utils_commandes import Commandes
from core.models import Tarif, CategorieTarif, Activite, Groupe, TypeCotisation, Caisse, TarifLigne, \
                                LISTE_METHODES_TARIFS, DICT_COLONNES_TARIFS, CombiTarif, Unite, Evenement, QuestionnaireQuestion
from core.widgets import DatePickerWidget, Formset
from parametrage.widgets import ParametresTarifs


class CombiTarifForm(forms.ModelForm):
    unites = forms.ModelMultipleChoiceField(label="", widget=Select2MultipleWidget(), queryset=Unite.objects.none(), required=False)

    class Meta:
        model = CombiTarif
        exclude = []

    def __init__(self, *args, activite, prefixe, **kwargs):
        super(CombiTarifForm, self).__init__(*args, **kwargs)
        self.activite = activite
        self.prefixe = prefixe

        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.fields['unites'].queryset = Unite.objects.filter(activite=activite).order_by("ordre")

        if "date" in self.fields:
            self.fields['date'].widget = DatePickerWidget()

        if "groupe" in self.fields:
            self.fields['groupe'].queryset = Groupe.objects.filter(activite=activite).order_by("ordre")

        if self.prefixe == "JOURN":
            self.fields['unites'].label = "Combinaisons d'unités conditionnelles"
            self.fields['unites'].help_text = """Sélectionnez la ou les unités de consommation qui vont déclencher ce tarif. Chaque ligne représente une combinaison possible.
                                                Cliquez sur Ajouter ci-dessous pour ajouter une nouvelle combinaison de déclenchement."""
        if self.prefixe == "FORFAIT":
            self.fields['unites'].label = "Combinaisons d'unités"
        if self.prefixe == "CREDIT":
            self.fields['unites'].label = "Combinaisons d'unités associables au forfait"

    def clean(self):
        if self.cleaned_data.get('DELETE') == False:

            # Vérifie qu'au moins une unité a été saisie
            if len(self.cleaned_data["unites"]) == 0:
                raise forms.ValidationError('Vous devez sélectionner au moins une unité')

            # Vérifie la ligne de type FORFAIT
            if self.prefixe == "FORFAIT":
                if self.cleaned_data["date"] == None:
                    raise forms.ValidationError('Vous devez saisir une date')
                # if self.cleaned_data["groupe"] == None:
                #     raise forms.ValidationError('Vous devez sélectionner un groupe')

        return self.cleaned_data


class BaseCombiTarifFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.activite = kwargs.get("activite", None)
        self.prefixe = kwargs["form_kwargs"].get("prefixe", None)
        super(BaseCombiTarifFormSet, self).__init__(*args, **kwargs)

    def get_queryset(self):
        """ Sélectionne uniquement les lignes qui correspondent au préfixe du formset """
        if not hasattr(self, '_queryset'):
            qs = super(BaseCombiTarifFormSet, self).get_queryset().filter(type=self.prefixe)
            self._queryset = qs
        return self._queryset

    def clean(self):
        index_ligne = 0
        liste_lignes_unites = []
        for form in self.forms:
            if self._should_delete_form(form) == False:

                # Vérification de la validité de la ligne
                if form.is_valid() == False or len(form.cleaned_data) == 0:
                    message = form.errors.as_data()["__all__"][0].message
                    raise forms.ValidationError("La ligne %d n'est pas valide : %s." % (index_ligne+1, message))

                # Vérifie que 2 lignes ne sont pas identiques sur les unités
                dict_ligne = form.cleaned_data
                if self.prefixe != "FORFAIT" and str(dict_ligne["unites"]) in liste_lignes_unites:
                    raise forms.ValidationError("Deux combinaisons d'unités semblent identiques")

                liste_lignes_unites.append(str(dict_ligne["unites"]))
                index_ligne += 1

        # Vérifie qu'au moins une ligne a été saisie
        if index_ligne == 0:
            raise forms.ValidationError("Vous devez saisir au moins une combinaison d'unités")


FORMSET_UNITES_JOURN = inlineformset_factory(Tarif, CombiTarif, form=CombiTarifForm, fk_name="tarif", formset=BaseCombiTarifFormSet,
                                            fields=["unites"], extra=0, min_num=1,
                                            can_delete=True, validate_max=True, can_order=False)

FORMSET_UNITES_FORFAIT = inlineformset_factory(Tarif, CombiTarif, form=CombiTarifForm, fk_name="tarif", formset=BaseCombiTarifFormSet,
                                            fields=["date", "groupe", "unites"], extra=0, min_num=1,
                                            can_delete=True, validate_max=True, can_order=False)

FORMSET_UNITES_CREDIT = inlineformset_factory(Tarif, CombiTarif, form=CombiTarifForm, fk_name="tarif", formset=BaseCombiTarifFormSet,
                                            fields=["unites", "quantite_max"], extra=0, min_num=1,
                                            can_delete=True, validate_max=True, can_order=False)





class Formulaire(FormulaireBase, ModelForm):
    # Dates de validité
    date_debut = forms.DateField(label="Date de début", required=True, widget=DatePickerWidget(), help_text="Saisissez obligatoirement la date de début d'application de ce tarif.")
    date_fin = forms.DateField(label="Date de fin", required=False, widget=DatePickerWidget(), help_text="Il est possible de définir une date de fin de validité, mais cela sera souvent inutile car en cas d'évolution tarifaire, vous créerez simplement un nouveau tarif qui viendra remplacer l'ancien à partir d'une date donnée.")

    # Catégories de tarifs
    categories_tarifs = forms.ModelMultipleChoiceField(label="Catégories de tarifs", widget=Select2MultipleWidget(), queryset=CategorieTarif.objects.none(), required=True, help_text="""
                                                        Vous devez obligatoirement sélectionner la ou les catégories de tarifs associés à ce tarif. Par exemple, sélectionnez une
                                                        catégorie 'Hors commune' si vous souhaitez que ce tarif s'applique uniquement aux individus inscrits avec la catégorie
                                                        de tarif correspondante.""")

    # Label prestation
    choix_label = [("NOM_TARIF", "Nom du tarif"), ("DESCRIPTION", "Description du tarif"), ("PERSO", "Un label personnalisé")]
    label_type = forms.TypedChoiceField(label="Label de la prestation", choices=choix_label, initial='NOM_TARIF', required=False, help_text="""La prestation générée automatiquement
                                        portera par défaut le label du 'nom de tarif' associé à ce tarif. Mais vous pouvez aussi choisir de donner à la prestation le nom correspondant au champ 
                                        'Description' du tarif (Voir plus sur cette page) ou un nom personnalisé à renseigner ci-dessous.""")
    # label_prestation = forms.CharField(label="Label personnalisé", required=False)

    # Conditions
    choix_groupes = [("TOUS", "Tous les groupes"), ("SELECTION", "Uniquement certains groupes")]
    groupes_type = forms.TypedChoiceField(label="Groupes associés", choices=choix_groupes, initial='TOUS', required=False, help_text="""A renseigner uniquement 
                                            si vous souhaitez que ce tarif ne s'applique qu'aux individus inscrits sur un ou plusieurs groupes donnés.""")
    groupes = forms.ModelMultipleChoiceField(label="Sélection des groupes", widget=Select2MultipleWidget(), queryset=Groupe.objects.none(), required=False)

    choix_cotisations = [("TOUS", "Toutes les adhésions"), ("SELECTION", "Uniquement certaines adhésions")]
    cotisations_type = forms.TypedChoiceField(label="Adhésions associées", choices=choix_cotisations, initial='TOUS', required=False, help_text="""A renseigner uniquement 
                                            si vous souhaitez que ce tarif ne s'applique qu'aux individus qui sont à jour d'un ou plusieurs types d'adhésions donnés.""")
    cotisations = forms.ModelMultipleChoiceField(label="Sélection des adhésions", widget=Select2MultipleWidget(), queryset=TypeCotisation.objects.all(), required=False)

    choix_caisses = [("TOUS", "Toutes les caisses"), ("SELECTION", "Uniquement certaines caisses")]
    caisses_type = forms.TypedChoiceField(label="Caisses associées", choices=choix_caisses, initial='TOUS', required=False, help_text="""A renseigner uniquement 
                                            si vous souhaitez que ce tarif ne s'applique qu'aux familles associées à une ou plusieurs caisses données.""")
    caisses = forms.ModelMultipleChoiceField(label="Sélection des caisses", widget=Select2MultipleWidget(), queryset=Caisse.objects.all(), required=False)

    choix_periodes = [("TOUS", "Toutes les périodes"), ("SELECTION", "Uniquement certaines périodes")]
    periodes_type = forms.TypedChoiceField(label="Périodes", choices=choix_periodes, initial='TOUS', required=False, help_text="""A renseigner uniquement 
                                            si vous souhaitez que ce tarif ne s'applique que sur une période donnée. Utile si vous avez par exemple des tarifs 
                                            différents les lundis et les mardis, ou les jours de vacances et les jours scolaires...""")

    # Forfait daté : Création de consommations
    choix_conso_forfait = [("SANS_CONSO", "Sans consommations"), ("CALENDRIER", "Créer les consommations selon le calendrier des ouvertures"), ("CHOIX_CONSO", "Créer les consommations suivantes")]
    conso_forfait_type = forms.TypedChoiceField(label="Consommations", choices=choix_conso_forfait, initial='SANS_CONSO', required=False, help_text="""
                                                Par défaut, aucune consommation ne sera générée automatiquement lors de l'application du tarif. Mais vous pouvez choisir
                                                de laisser l'application créer automatiquement des consommations dans la grille des consommations de l'individu lorsque
                                                ce tarif sera appliqué. Cela est par exemple utile pour appliquer une prestation forfaitaire pour un séjour et créer en
                                                même temps les consommations pour chaque date du séjour.""")

    # Forfait daté : Date de facturation
    choix_date_facturation_forfait = [("DATE_DEBUT_FORFAIT", "Date de début du forfait"), ("DATE_SAISIE", "Date de la saisie du forfait"), ("DATE_DEBUT_ACTIVITE", "Date de début de l'activité"), ("DATE", "Une date donnée")]
    date_facturation_forfait_type = forms.TypedChoiceField(label="Date de facturation", choices=choix_date_facturation_forfait, initial='DATE_DEBUT_FORFAIT', required=False, help_text="""
                                                            La date de la prestation générée sera par défaut celle du début du forfait, mais vous pouvez choisir un autre
                                                            type de date dans la liste proposée.""")
    date_facturation_forfait = forms.DateField(label="Date de facturation", required=False, widget=DatePickerWidget(), help_text="""Par défaut, la date de la prestation sera
                                                    celle du début du forfait, mais vous pouvez choisir un autre type de date dans la liste proposée.""")

    # Forfait-crédit : Automatique
    type_application = forms.TypedChoiceField(label="Application", choices=[
        ("MANUEL", "Manuelle"),
        #("AUTO", "Automatique")
    ], initial="MANUEL", required=False)
    forfait_auto_nbre_conso_min = forms.IntegerField(label="Nbre conso min.", required=False, initial=2, validators=[MinValueValidator(1)], help_text="Ce forfait sera appliqué automatiquement si le nombre de consommations existantes sur la période est supérieur ou égal à X.")
    forfait_auto_debut = forms.TypedChoiceField(label="Début du forfait", initial="PREC_SEMAINE_PREMIER_JOUR", required=False, choices=[
        ("PREC_LUNDI", "Lundi précédent"), ("PREC_MARDI", "Mardi précédent"), ("PREC_MERCREDI", "Mercredi précédent"), ("PREC_JEUDI", "Jeudi précédent"),
        ("PREC_VENDREDI", "Vendredi précédent"), ("PREC_SAMEDI", "Samedi précédent"), ("PREC_DIMANCHE", "Dimanche précédent"),
        ("PREC_SEMAINE_PREMIER_JOUR", "1er jour de la semaine"), ("PREC_MOIS_PREMIER_JOUR", "1er jour du mois"),
        # ("PREC_JOUR", "Le jour de la première consommation saisie"),
        # ("PREC_JOUR_MOINS_1", "Jour J-1"), ("PREC_JOUR_MOINS_2", "Jour J-2"), ("PREC_JOUR_MOINS_3", "Jour J-3"), ("PREC_JOUR_MOINS_4", "Jour J-4"),
        # ("PREC_JOUR_MOINS_5", "Jour J-5"), ("PREC_JOUR_MOINS_6", "Jour J-6"), ("PREC_JOUR_MOINS_7", "Jour J-7"),
        ("PREC_MOIS_1", "1er janvier précédent"), ("PREC_MOIS_2", "1er février précédent"), ("PREC_MOIS_3", "1er mars précédent"),
        ("PREC_MOIS_4", "1er avril précédent"),("PREC_MOIS_5", "1er mai précédent"), ("PREC_MOIS_6", "1er juin précédent"),
        ("PREC_MOIS_7", "1er juillet précédent"),("PREC_MOIS_8", "1er août précédent"), ("PREC_MOIS_9", "1er septembre précédent"),
        ("PREC_MOIS_10", "1er octobre précédent"),("PREC_MOIS_11", "1er novembre précédent"), ("PREC_MOIS_12", "1er décembre précédent"),
    ])
    forfait_auto_fin = forms.TypedChoiceField(label="Fin du forfait", initial="SUIV_SEMAINE_VENDREDI", required=False, choices=[
        ("SUIV_LUNDI", "Lundi suivant"), ("SUIV_MARDI", "Mardi suivant"), ("SUIV_MERCREDI", "Mercredi suivant"), ("SUIV_JEUDI", "Jeudi suivant"),
        ("SUIV_VENDREDI", "Vendredi suivant"), ("SUIV_SAMEDI", "Samedi suivant"), ("SUIV_DIMANCHE", "Dimanche suivant"),
        ("SUIV_SEMAINE_DERNIER_JOUR", "Dernier jour de la semaine"), ("SUIV_SEMAINE_VENDREDI", "Vendredi de la semaine"), ("SUIV_SEMAINE_SAMEDI", "Samedi de la semaine"),
        ("SUIV_MOIS_DERNIER_JOUR", "Dernier jour du mois"),
        # ("SUIV_JOUR", "Le jour de la première consommation saisie"),
        # ("SUIV_JOUR_PLUS_1", "Jour J+1"), ("SUIV_JOUR_PLUS_2", "Jour J+2"), ("SUIV_JOUR_PLUS_3", "Jour J+3"), ("SUIV_JOUR_PLUS_4", "Jour J+4"),
        # ("SUIV_JOUR_PLUS_5", "Jour J+5"), ("PREC_JOUR_PLUS_6", "Jour J+6"), ("SUIV_JOUR_PLUS_7", "Jour J+7"),
        ("SUIV_MOIS_1", "Dernier jour du mois de janvier suivant"), ("SUIV_MOIS_2", "Dernier jour du mois de février suivant"), ("SUIV_MOIS_3", "Dernier jour du mois de mars suivant"),
        ("SUIV_MOIS_4", "Dernier jour du mois de avril suivant"),("SUIV_MOIS_5", "Dernier jour du mois de mai suivant"), ("SUIV_MOIS_6", "Dernier jour du mois de juin suivant"),
        ("SUIV_MOIS_7", "Dernier jour du mois de juillet suivant"),("SUIV_MOIS_8", "Dernier jour du mois de août suivant"), ("SUIV_MOIS_9", "Dernier jour du mois de septembre suivant"),
        ("SUIV_MOIS_10", "Dernier jour du mois de octobre suivant"),("SUIV_MOIS_11", "Dernier jour du mois de novembre suivant"), ("SUIV_MOIS_12", "Dernier jour du mois de décembre suivant"),
    ])

    # Forfait-crédit : Durée de validité
    choix_duree_forfait = [("NON", "Sans durée par défaut"), ("OUI", "Avec une durée par défaut")]
    validite_duree_forfait = forms.TypedChoiceField(label="Durée par défaut", choices=choix_duree_forfait, initial='NON', required=False, help_text="""
                                                    Vous pouvez définir ici la durée par défaut du forfait à partir de la date du début. Exemple : 5 jours...""")
    validite_jours = forms.IntegerField(label="Jours", required=False)
    validite_mois = forms.IntegerField(label="Mois", required=False)
    validite_annees = forms.IntegerField(label="Années", required=False)

    # Forfait-crédit : Blocage plafond
    blocage_plafond = forms.BooleanField(label="Bloquer si la quantité maximale de consommations est atteinte", required=False, help_text="""
                                            Cochez cette case uniquement si la quantité maximale que vous avez renseigné ci-dessus doit bloquer la saisie
                                            des consommations. Par exemple, si la quantité maximale de 'matin' est de 5, il sera impossible d'associer plus de 5 matins
                                            avec ce forfait.""")

    # Forfait-crédit : Date de facturation
    choix_date_facturation_credit = [("DATE_DEBUT_FORFAIT", "Date de début du forfait"), ("DATE_SAISIE", "Date de la saisie du forfait"), ("DATE", "Une date donnée")]
    date_facturation_credit_type = forms.TypedChoiceField(label="Date de facturation", choices=choix_date_facturation_credit, initial='DATE_DEBUT_FORFAIT', required=False, help_text="""
                                                        Par défaut, la date de la prestation sera celle du début du forfait, mais vous pouvez sélectionner un autre type
                                                        de date dans la liste proposée.""")
    date_facturation_credit = forms.DateField(label="Date de facturation", required=False, widget=DatePickerWidget())

    # Lignes de tarifs
    tarifs_lignes_data = forms.CharField(required=False)
    attrs = {
        'liste_methodes_tarifs': LISTE_METHODES_TARIFS,
        'dict_colonnes_tarifs': DICT_COLONNES_TARIFS,
        'id_ctrl_methode': "id_methode",
        'id': "parametres_tarif",
        'id_tarifs_lignes_data': "tarifs_lignes_data",
        'id_form': 'activites_tarifs_form',
    }
    parametres_tarif = forms.CharField(label="Paramètres", widget=ParametresTarifs(attrs=attrs), required=False)

    class Meta:
        model = Tarif
        fields = "__all__"
        help_texts = {
            "description": "Il est possible de définir une description rapide pour vous aider à vous souvenir des caractéristiques de ce tarif. Exemple : Tarif pour les individus hors-commune uniquement...",
            "observations": "Si vous souhaitez ajouter un commentaire au sujet de ce tarif.",
            "code_compta": "Renseignez ici le code comptable de l'activité uniquement si vous souhaitez faire un export des écritures comptables vers des logiciels de comptabilité tiers.",
            "tva": "Saisissez si besoin un taux de TVA si votre activité est soumise à la collecte de la TVA. Attention, notez que cette application n'est pas un logiciel de caisse certifié pour la collecte de la TVA.",
            "type": """Sélectionnez obligatoirement un type de tarif. Le type 'Prestation journalière' est le plus utilisé, il permet de déclencher ce tarif lorsqu'une ou plusieurs
                        unités de consommation sont sélectionnées dans la grille des consommations. Le 'forfait daté' permet notamment d'appliquer un tarif forfaitaire à
                        l'inscription (Pour une activité yoga annuelle par exemple). Le 'forfait crédit' permet d'appliquer un forfait pour une période donnée et d'y associer
                        automatiquement certaines consommations.""",
            "etats": "Cochez le ou les états de consommation qui vont déclencher ce tarif.",
            "forfait_saisie_manuelle": """En cochant cette case, vous autorisez l'utilisateur à saisir ce tarif forfaitaire manuellement depuis la grille 
                                        des consommations. Si vous souhaitez que ce tarif forfaitaire s'applique uniquement à l'inscription, ne cochez pas cette case.""",
            "forfait_saisie_auto": """Cochez cette case si vous souhaitez que ce tarif forfaitaire s'applique automatiquement lors de l'inscription initiale de 
                                        l'individu à l'activité. Utile notamment pour des activités limitées dans le temps. Exemples : 'Yoga - Saison 2024-25' ou 'Séjour à la
                                        neige - Février 2026'...""",
            "forfait_suppression_auto": """Si vous avez coché la case ci-dessus, cochez également cette case pour permettre à l'application de supprimer automatiquement la 
                                            prestation forfaitaire si on désinscrit l'individu de l'activité.""",
            "date_facturation_forfait": "Par défaut, la date de la prestation sera celle du début du forfait, mais vous pouvez choisir un autre type de date dans la liste.",
            "forfait_beneficiaire": "Sélectionnez 'famille' si le forfait est commun à tous les membres de la famille, sinon sélectionnez 'individu'.",
            "methode": "Sélectionnez une méthode de calcul dans la liste proposée puis renseignez les paramètres ci-dessous.",
        }

    def __init__(self, *args, **kwargs):
        idactivite = kwargs.pop("idactivite")
        nom_tarif = kwargs.pop("categorie", None)
        idevenement = kwargs.pop("evenement", None)
        methode = kwargs.pop("methode", None)
        tarifs_lignes_data = kwargs.pop("tarifs_lignes_data", None)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'activites_tarifs_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Définit l'activité associée
        activite = Activite.objects.get(pk=idactivite)

        # Si c'est un tarif associé à un événement
        if idevenement:
            evenement = Evenement.objects.get(pk=idevenement)
            self.fields['date_debut'].initial = evenement.date
            self.fields['date_debut'].widget = HiddenInput()
            self.fields['date_fin'].initial = evenement.date
            self.fields['date_fin'].widget = HiddenInput()
            self.fields['type'].initial = "EVENEMENT"
            self.fields['type'].disabled = True
        else:
            # On enlève EVENEMENT de la liste des choix possibles
            liste_choix = self.fields['type'].choices
            liste_choix.pop(4)
            self.fields['type'].choices = liste_choix

        # Filtrage pour l'activité
        self.fields['categories_tarifs'].queryset = CategorieTarif.objects.all().filter(activite=activite)
        self.fields['groupes'].queryset = Groupe.objects.all().filter(activite=activite)
        # self.fields['nom_tarif'].queryset = NomTarif.objects.all().filter(activite=activite)

        # Label perso
        if self.instance.label_prestation in ("NOM_TARIF", "nom_tarif", None, ""):
            self.fields['label_type'].initial = "NOM_TARIF"
            self.fields['label_prestation'].initial = None
        elif self.instance.label_prestation in ("DESCRIPTION", "description_tarif"):
            self.fields['label_type'].initial = "DESCRIPTION"
            self.fields['label_prestation'].initial = None
        else:
            self.fields['label_type'].initial = "PERSO"

        # Conditions d'application
        if self.instance.pk:
            if self.instance.groupes.count() > 0:
                self.fields['groupes_type'].initial = "SELECTION"
            if self.instance.cotisations.count() > 0:
                self.fields['cotisations_type'].initial = "SELECTION"
            if self.instance.caisses.count() > 0:
                self.fields['caisses_type'].initial = "SELECTION"
            if self.instance.jours_scolaires or self.instance.jours_vacances:
                self.fields['periodes_type'].initial = "SELECTION"

        # Forfait-crédit : Génération de conso
        if self.instance.type == "FORFAIT":
            if self.instance.options != None and "calendrier" in self.instance.options:
                self.fields['conso_forfait_type'].initial = "CALENDRIER"
            if CombiTarif.objects.filter(tarif=self.instance).count() > 0:
                self.fields['conso_forfait_type'].initial = "CHOIX_CONSO"

        # Forfait daté : Date de facturation
        if self.instance.date_facturation != None:
            if self.instance.date_facturation == "date_saisie":
                self.fields['date_facturation_forfait_type'].initial = "DATE_SAISIE"
            if self.instance.date_facturation == "date_debut_activite":
                self.fields['date_facturation_forfait_type'].initial = "DATE_DEBUT_ACTIVITE"
            if self.instance.date_facturation.startswith("date:"):
                self.fields['date_facturation_forfait_type'].initial = "DATE"
                self.fields['date_facturation_forfait'].initial = parse_date(self.instance.date_facturation[5:]).strftime('%d/%m/%Y')

        # Validité
        self.fields["validite_jours"].widget.attrs.update({"min": 0})
        self.fields["validite_mois"].widget.attrs.update({"min": 0})
        self.fields["validite_annees"].widget.attrs.update({"min": 0})

        # Forfait-crédit : Durée de validité
        if self.instance.forfait_duree != None:
            self.fields['validite_duree_forfait'].initial = "OUI"
            jours, mois, annees = self.instance.forfait_duree.split("-")
            self.fields['validite_jours'].initial = int(jours[1:])
            self.fields['validite_mois'].initial = int(mois[1:])
            self.fields['validite_annees'].initial = int(annees[1:])

        # Forfait-crédit : Blocage plafond
        if self.instance.options != None and "blocage_plafond" in self.instance.options:
            self.fields['blocage_plafond'].initial = True

        # Forfait-crédit : Date de facturation
        if self.instance.date_facturation != None:
            if self.instance.date_facturation == "date_saisie":
                self.fields['date_facturation_credit_type'].initial = "DATE_SAISIE"
            if self.instance.date_facturation.startswith("date:"):
                self.fields['date_facturation_credit_type'].initial = "DATE"
                self.fields['date_facturation_credit'].initial = parse_date(self.instance.date_facturation[5:]).strftime('%d/%m/%Y')

        # Forfait-crédit : Automatique
        self.fields["forfait_auto_nbre_conso_min"].widget.attrs["min"] = 1
        if self.instance.forfait_auto:
            self.fields["type_application"].initial = "AUTO"
            for key, valeur in json.loads(self.instance.forfait_auto).items():
                self.fields["forfait_auto_%s" % key].initial = valeur

        # Etats conditionnels
        if not self.instance.pk:
            self.fields['etats'].initial = ["reservation", "present", "absenti"]

        # Méthode
        self.fields["methode"].choices = [(dict_methode["code"], dict_methode["label"]) for dict_methode in LISTE_METHODES_TARIFS if "PRODUIT" not in dict_methode["tarifs_compatibles"]]

        # Paramètres du tarif
        if self.instance.methode:
            liste_colonnes = []
            champs = GetDictMethode(self.instance.methode)["champs"] if GetDictMethode(self.instance.methode) else []
            for nom_champ in champs:
                liste_colonnes.append((nom_champ, DICT_COLONNES_TARIFS[nom_champ]))

            if tarifs_lignes_data:
                tarifs_lignes_data = json.loads(tarifs_lignes_data)
            else:
                tarifs_lignes_data = []
                liste_lignes = TarifLigne.objects.filter(tarif_id=self.instance.pk).order_by("num_ligne")
                for ligne in liste_lignes:
                    ligne_data = []
                    dict_ligne = model_to_dict(ligne)
                    for nom_champ, dict_colonne in liste_colonnes:
                        valeur = dict_ligne[nom_champ]
                        if isinstance(valeur, decimal.Decimal):
                            valeur = float(valeur)
                        if dict_colonne["editeur"] == "questionnaire":
                            if valeur == None: valeur = ''
                        elif dict_colonne["editeur"] in ("decimal", "decimal4"):
                            if valeur == None: valeur = 0
                            valeur = float(valeur)
                        elif valeur and dict_colonne["editeur"] == "heure":
                            valeur = valeur.strftime('%H:%M')
                            if valeur == None: valeur = ''
                        elif dict_colonne["editeur"] == "date":
                            valeur = valeur.strftime('%d/%m/%Y')
                            if valeur == None: valeur = ''
                        else:
                            if valeur == None: valeur = ''
                        ligne_data.append(valeur)
                    tarifs_lignes_data.append(ligne_data)
                methode = self.instance.methode

            self.fields['parametres_tarif'].widget.attrs.update({
                'methode': methode,
                'tarifs_lignes_data': mark_safe(json.dumps(tarifs_lignes_data)),
                'questionnaires': json.dumps([{"id": question.pk, "name": question.label} for question in QuestionnaireQuestion.objects.filter(controle__in=("decimal", "montant"))]),
            })

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('activite', value=activite.idactivite),
            Hidden('nom_tarif', value=nom_tarif),
            TabHolder(
                Tab("Généralités",
                    Field("date_debut"),
                    Field("date_fin"),
                    Field("description"),
                    Field("observations"),
                    Field("categories_tarifs"),
                    Fieldset("Label de la prestation",
                        Field("label_type"),
                        Field("label_prestation"),
                    ),
                    Field("code_compta"),
                    PrependedText('tva', '%'),
                ),
                Tab("Conditions d'application",
                    Fieldset("Groupes associés",
                        Field("groupes_type"),
                        Field("groupes"),
                    ),
                    Fieldset("Cotisations associées",
                        Field("cotisations_type"),
                        Field("cotisations"),
                    ),
                    Fieldset("Caisses associées",
                        Field("caisses_type"),
                        Field("caisses"),
                    ),
                    Fieldset("Périodes",
                        Field("periodes_type"),
                        InlineCheckboxes("jours_scolaires"),
                        InlineCheckboxes("jours_vacances"),
                    ),
                ),
                Tab("Type de tarif",
                    Field("type"),
                    # Prestation journalière
                    Div(
                        Div(
                            HTML("<label class='col-form-label col-md-2 requiredField'>Paramètres*</label>"),
                            Div(
                                Formset("formset_unites_journ"),
                                css_class="controls col-md-10"
                            ),
                            css_class="form-group row"
                        ),
                        InlineCheckboxes("etats"),
                        Field("penalite"),
                        PrependedText("penalite_pourcentage", "%"),
                        Field("penalite_label"),
                        id="div_type_journ"
                    ),
                    # Forfait daté
                    Div(
                        Field("conso_forfait_type"),
                        Div(
                            HTML("<label class='col-form-label col-md-2 requiredField'>Paramètres*</label>"),
                            Div(
                                Formset("formset_unites_forfait"),
                                css_class="controls col-md-10"
                            ),
                            css_class="form-group row",
                            id="div_formset_unites_forfait"
                        ),
                        Field("forfait_saisie_manuelle"),
                        Field("forfait_saisie_auto"),
                        Field("forfait_suppression_auto"),
                        Field("date_facturation_forfait_type"),
                        Field("date_facturation_forfait"),
                        id="div_type_forfait"
                    ),
                    # Forfait crédit
                    Div(
                        Div(
                            HTML("<label class='col-form-label col-md-2 requiredField'>Paramètres*</label>"),
                            Div(
                                Formset("formset_unites_credit"),
                                css_class="controls col-md-10"
                            ),
                            css_class="form-group row"
                        ),
                        Field("blocage_plafond"),
                        Field("forfait_beneficiaire"),
                        Field("date_facturation_credit_type"),
                        Field("date_facturation_credit"),
                        Field("type_application"),
                        Fieldset("Paramètres du forfait automatique",
                            HTML("""<div class='alert alert-warning alert-dismissible'><i class='icon fa fa-warning'></i>L'application automatique est une fonction expérimentale. A utiliser avec vigilance.</div>"""),
                            Field("forfait_auto_nbre_conso_min"),
                            Field("forfait_auto_debut"),
                            Field("forfait_auto_fin"),
                            id="div_parametres_forfait_auto",
                        ),
                        Fieldset('Durée par défaut',
                            Field('validite_duree_forfait'),
                            Div(
                                Field('validite_annees'),
                                Field('validite_mois'),
                                Field('validite_jours'),
                                id='bloc_duree_forfait'
                            ),
                             id="div_validite_duree_forfait",
                        ),
                        id="div_type_credit"
                    ),
                ),
                Tab("Calcul du tarif",
                    Field("methode"),
                    Hidden("tarifs_lignes_data", value='', id='tarifs_lignes_data'),
                    # HTML(TABLEAU_TARIFS_LIGNES),
                    Field("parametres_tarif"),
                    Field("type_quotient"),
                    Field("facturation_unite"),
                ),
            ),
            HTML(EXTRA_SCRIPT),
        )

        # Si c'est un tarif d'événement, on ajoute cette ligne
        if idevenement:
            self.helper.layout.append(Hidden('evenement', value=idevenement))

    def clean(self):
        # Label de la prestation
        if self.cleaned_data["label_type"] == "PERSO":
            if self.cleaned_data["label_prestation"] == None:
                self.add_error('label_prestation', "Vous devez saisir un label de prestation personnalisé")
                return
        elif self.cleaned_data["label_type"] == "DESCRIPTION":
            if self.cleaned_data["description"]== None:
                self.add_error('description', "Vous devez saisir une description qui sera utilisée en tant que label de prestation")
                return
            self.cleaned_data["label_prestation"] = "description_tarif"
        else:
            self.cleaned_data["label_prestation"] = "nom_tarif"

        # Groupes associés
        if self.cleaned_data["groupes_type"] == "SELECTION":
            if len(self.cleaned_data["groupes"]) == 0:
                self.add_error('groupes', "Vous devez cocher au moins un groupe")
                return
        else:
            self.cleaned_data["groupes"] = []

        # Cotisations associées
        if self.cleaned_data["cotisations_type"] == "SELECTION":
            if len(self.cleaned_data["cotisations"]) == 0:
                self.add_error('cotisations', "Vous devez cocher au moins une cotisation")
                return
        else:
            self.cleaned_data["cotisations"] = []

        # Caisses associés
        if self.cleaned_data["caisses_type"] == "SELECTION":
            if len(self.cleaned_data["caisses"]) == 0:
                self.add_error('caisses', "Vous devez cocher au moins une caisse")
                return
        else:
            self.cleaned_data["caisses"] = []

        # Pénalité
        if self.cleaned_data["penalite"] == "pourcentage":
            if not self.cleaned_data["penalite_pourcentage"]:
                self.add_error("penalite_pourcentage", "Vous devez saisir un pourcentage valide")
                return

        # Forfait daté : Génération de consommations
        if self.cleaned_data["type"] == "FORFAIT":
            if self.cleaned_data["conso_forfait_type"] == "CALENDRIER":
                self.cleaned_data["options"] = "calendrier"

        # Forfait daté : Date de facturation
        if self.cleaned_data["type"] == "FORFAIT":
            if self.cleaned_data["date_facturation_forfait_type"] == "DATE":
                if self.cleaned_data["date_facturation_forfait"] == None:
                    self.add_error('date_facturation_forfait', "Vous devez saisir une date de facturation")
                    return
                self.cleaned_data["date_facturation"] = "date:%s" % self.cleaned_data["date_facturation_forfait"]
            else:
                self.cleaned_data["date_facturation"] = self.cleaned_data["date_facturation_forfait_type"].lower()
            if self.cleaned_data["methode"] not in ("montant_unique", "qf", "choix"):
                self.add_error('methode', "Le type 'Forfait daté' n'est compatible qu'avec les méthodes 'Montant unique', 'En fonction du QF' et 'au choix'.")
                return

        # Forfait crédit : Automatique
        if self.cleaned_data["type"] == "CREDIT" and self.cleaned_data["type_application"] == "AUTO" and self.cleaned_data["forfait_beneficiaire"] == "individu":
            self.cleaned_data["forfait_auto"] = json.dumps({
                "nbre_conso_min" : self.cleaned_data["forfait_auto_nbre_conso_min"],
                "debut": self.cleaned_data["forfait_auto_debut"],
                "fin": self.cleaned_data["forfait_auto_fin"],
            })
        else:
            self.cleaned_data["forfait_auto"] = None

        # Durée par défaut si forfait-crédit
        if self.cleaned_data["validite_duree_forfait"] == "OUI":
            jours = int(self.cleaned_data["validite_jours"] or 0)
            mois = int(self.cleaned_data["validite_mois"] or 0)
            annees = int(self.cleaned_data["validite_annees"] or 0)
            if jours == 0 and mois == 0 and annees == 0:
                self.add_error('validite_duree_forfait', "Vous devez saisir une durée en jours et/ou mois et/ou années")
                return
            self.cleaned_data["forfait_duree"] = "j%d-m%d-a%d" % (jours, mois, annees)

        # Blocage plafond
        if self.cleaned_data["blocage_plafond"] == True:
            self.cleaned_data["options"] = "blocage_plafond"

        # Forfait crédit : Date de facturation
        if self.cleaned_data["type"] == "CREDIT":
            if self.cleaned_data["date_facturation_credit_type"] == "DATE":
                if self.cleaned_data["date_facturation_credit"] == None:
                    self.add_error('date_facturation_credit', "Vous devez saisir une date de facturation")
                    return
                self.cleaned_data["date_facturation"] = "date:%s" % self.cleaned_data["date_facturation_credit"]
            else:
                self.cleaned_data["date_facturation"] = self.cleaned_data["date_facturation_credit_type"].lower()

        # Lignes de tarifs
        liste_lignes_resultats = []
        if "tarifs_lignes_data" in self.cleaned_data and len(self.cleaned_data["tarifs_lignes_data"]) > 0:
            tarifs_lignes_data = json.loads(self.cleaned_data["tarifs_lignes_data"])
            code_methode = self.cleaned_data["methode"]
            liste_lignes_resultats = Clean_tarifs_lignes_data(tarifs_lignes_data=tarifs_lignes_data, code_methode=code_methode)

        self.cleaned_data["tarifs_lignes_data_resultats"] = liste_lignes_resultats

        return self.cleaned_data


def Clean_tarifs_lignes_data(tarifs_lignes_data=[], code_methode=""):
    dict_methode = GetDictMethode(code_methode)
    liste_champs_obligatoires = dict_methode["champs_obligatoires"]
    liste_lignes_resultats = []

    liste_colonnes = []
    for nom_champ in dict_methode["champs"]:
        liste_colonnes.append((nom_champ, DICT_COLONNES_TARIFS[nom_champ]))

    liste_resultats = []
    index_ligne = 0
    for ligne in tarifs_lignes_data:
        dict_ligne = {}
        index_colonne = 0

        # Vérifie les valeurs de chaque colonne
        for valeur in ligne:
            code_colonne, dict_colonne = liste_colonnes[index_colonne]

            def RaiseError():
                raise ValidationError("Paramètres du tarif : La valeur '%s' de la ligne %d n'est pas valide ! " % (
                dict_colonne["label"], index_ligne + 1))

            # Vérification des valeurs
            if valeur == "":
                valeur = None

            if valeur and dict_colonne["editeur"] in ("decimal", "decimal4"):
                try:
                    valeur = float(valeur)
                except:
                    RaiseError()

            if valeur and dict_colonne["editeur"] == "heure":
                try:
                    valeur = parse_time(valeur)
                except:
                    RaiseError()

            if valeur and dict_colonne["editeur"] == "date":
                try:
                    # valeur = datetime.datetime.strptime(valeur, "%d/%m/%Y").date() # Cette ne semble pas fonctionner avec le tarif selon date
                    valeur = parse_date(valeur[:10])
                except Exception as err:
                    print("erreur=", err)
                    RaiseError()

            if valeur not in ("", None):
                dict_ligne[code_colonne] = valeur
            index_colonne += 1

        # Vérifie que les champs obligatoires ont bien été renseignés sur la ligne
        for nom_champ in liste_champs_obligatoires:
            if nom_champ not in dict_ligne:
                label_colonne = DICT_COLONNES_TARIFS[nom_champ]["label"]
                raise ValidationError(
                    "Paramètres du tarif : Vous devez obligatoirement renseigner la valeur '%s' de la ligne %d ! " % (
                    label_colonne, index_ligne + 1))

        liste_lignes_resultats.append(dict_ligne)
        index_ligne += 1

    return liste_lignes_resultats

def GetDictMethode(code=""):
    for dict_methode in LISTE_METHODES_TARIFS:
        if dict_methode["code"] == code:
            return dict_methode
    return None




EXTRA_SCRIPT = """
{{ form.errors }}
{% if form.errors %}
    {% for field in form %}
        {% for error in field.errors %}
            <p> {{ error }} </p>
        {% endfor %}
    {% endfor %}
{% endif %}

<script>


// label_type
function On_change_label_type() {
    $('#div_id_label_prestation').hide();
    if($(this).val() == 'PERSO') {
        $('#div_id_label_prestation').show();
    }
}
$(document).ready(function() {
    $('#id_label_type').change(On_change_label_type);
    On_change_label_type.call($('#id_label_type').get(0));
});


// groupes_type
function On_change_groupes_type() {
    $('#div_id_groupes').hide();
    if($(this).val() == 'SELECTION') {
        $('#div_id_groupes').show();
    }
}
$(document).ready(function() {
    $('#id_groupes_type').change(On_change_groupes_type);
    On_change_groupes_type.call($('#id_groupes_type').get(0));
});

// cotisations_type
function On_change_cotisations_type() {
    $('#div_id_cotisations').hide();
    if($(this).val() == 'SELECTION') {
        $('#div_id_cotisations').show();
    }
}
$(document).ready(function() {
    $('#id_cotisations_type').change(On_change_cotisations_type);
    On_change_cotisations_type.call($('#id_cotisations_type').get(0));
});

// caisses_type
function On_change_caisses_type() {
    $('#div_id_caisses').hide();
    if($(this).val() == 'SELECTION') {
        $('#div_id_caisses').show();
    }
}
$(document).ready(function() {
    $('#id_caisses_type').change(On_change_caisses_type);
    On_change_caisses_type.call($('#id_caisses_type').get(0));
});

// periodes_type
function On_change_periodes_type() {
    $('#div_id_jours_scolaires').hide();
    $('#div_id_jours_vacances').hide();
    if($(this).val() == 'SELECTION') {
        $('#div_id_jours_scolaires').show();
        $('#div_id_jours_vacances').show();
    }
}
$(document).ready(function() {
    $('#id_periodes_type').change(On_change_periodes_type);
    On_change_periodes_type.call($('#id_periodes_type').get(0));
});

// type de tarifs
function On_change_type() {
    $('#div_type_journ').hide();
    $('#div_type_forfait').hide();
    $('#div_type_credit').hide();
    if($(this).val() == 'JOURN') {
        $('#div_type_journ').show();
    }
    if($(this).val() == 'FORFAIT') {
        $('#div_type_forfait').show();
    }
    if($(this).val() == 'CREDIT') {
        $('#div_type_credit').show();
    }
}
$(document).ready(function() {
    $('#id_type').change(On_change_type);
    On_change_type.call($('#id_type').get(0));
});

// Pénalité
function On_change_penalite() {
    $('#div_id_penalite_pourcentage').hide();
    $('#div_id_penalite_label').hide();
    if($(this).val() == 'pourcentage') {
        $('#div_id_penalite_pourcentage').show();
        $('#div_id_penalite_label').show();
    }
}
$(document).ready(function() {
    $('#id_penalite').change(On_change_penalite);
    On_change_penalite.call($('#id_penalite').get(0));
});

// conso_forfait_type
function On_change_conso_forfait_type() {
    $('#div_formset_unites_forfait').hide();
    if($(this).val() == 'CHOIX_CONSO') {
        $('#div_formset_unites_forfait').show();
    }
}
$(document).ready(function() {
    $('#id_conso_forfait_type').change(On_change_conso_forfait_type);
    On_change_conso_forfait_type.call($('#id_conso_forfait_type').get(0));
});

// validite_duree_forfait
function On_change_validite_duree_forfait() {
    $('#bloc_duree_forfait').hide();
    if($(this).val() == 'OUI') {
        $('#bloc_duree_forfait').show();
    }
}
$(document).ready(function() {
    $('#id_validite_duree_forfait').change(On_change_validite_duree_forfait);
    On_change_validite_duree_forfait.call($('#id_validite_duree_forfait').get(0));
});

// date_facturation_credit_type
function On_change_date_facturation_credit_type() {
    $('#div_id_date_facturation_credit').hide();
    if($(this).val() == 'DATE') {
        $('#div_id_date_facturation_credit').show();
    }
}
$(document).ready(function() {
    $('#id_date_facturation_credit_type').change(On_change_date_facturation_credit_type);
    On_change_date_facturation_credit_type.call($('#id_date_facturation_credit_type').get(0));
});

// date_facturation_forfait_type
function On_change_date_facturation_forfait_type() {
    $('#div_id_date_facturation_forfait').hide();
    if($(this).val() == 'DATE') {
        $('#div_id_date_facturation_forfait').show();
    }
}
$(document).ready(function() {
    $('#id_date_facturation_forfait_type').change(On_change_date_facturation_forfait_type);
    On_change_date_facturation_forfait_type.call($('#id_date_facturation_forfait_type').get(0));
});

// forfait_beneficiaire
function On_change_forfait_beneficiaire() {console.log("coucou");
    $('#div_id_type_application').hide();
    if ($(this).val() == 'individu') {
        $('#div_id_type_application').show();
    }
    On_change_type_application.call($('#id_type_application').get(0));
}
$(document).ready(function() {
    $('#id_forfait_beneficiaire').change(On_change_forfait_beneficiaire);
    On_change_forfait_beneficiaire.call($('#id_forfait_beneficiaire').get(0));
});

// type_application
function On_change_type_application() {
    $('#div_parametres_forfait_auto').hide();
    $('#div_validite_duree_forfait').hide();
    if (($(this).val() == 'AUTO') & ($('#id_forfait_beneficiaire').val() == 'individu')) {
        $('#div_parametres_forfait_auto').show();
    }
    if (($(this).val() == 'MANUEL') | ($('#id_forfait_beneficiaire').val() == 'famille')) {
        $('#div_validite_duree_forfait').show();
    }
}
$(document).ready(function() {
    $('#id_type_application').change(On_change_type_application);
    On_change_type_application.call($('#id_type_application').get(0));
});

</script>
"""
