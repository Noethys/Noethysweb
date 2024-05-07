# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django import forms
from django.forms import ModelForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, HTML, Fieldset
from crispy_forms.bootstrap import Field, PrependedText
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Reglement, ModeReglement, Emetteur, Payeur, CompteBancaire, Facture
from core.widgets import DatePickerWidget, Select_avec_commandes
from core.utils import utils_preferences, utils_dates
from fiche_famille.widgets import Selection_emetteur, Selection_mode_reglement, Saisie_ventilation


class Formulaire(FormulaireBase, ModelForm):
    date = forms.DateField(label="Date", required=True, widget=DatePickerWidget())
    mode = forms.ModelChoiceField(label="Mode de règlement", queryset=ModeReglement.objects.all().order_by("label"), widget=Selection_mode_reglement(), required=True)
    emetteur = forms.ModelChoiceField(label="Emetteur", queryset=Emetteur.objects.all().order_by("nom"), widget=Selection_emetteur(), required=False)
    payeur = forms.ModelChoiceField(label="Payeur", queryset=Payeur.objects.none(), widget=Select_avec_commandes(), required=True)
    observations = forms.CharField(label="Observations", widget=forms.Textarea(attrs={'rows': 1}), required=False)
    date_differe = forms.DateField(label="Encaissement différé", required=False, widget=DatePickerWidget())
    ventilation = forms.CharField(label="Ventilation", widget=Saisie_ventilation(), required=False)

    class Meta:
        model = Reglement
        fields = ["famille", "date", "mode", "emetteur", "payeur", "observations", "date_differe", "numero_quittancier", "montant", "numero_piece", "compte", ]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        idfacture = kwargs.pop("idfacture")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_reglements_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        # Date
        if not self.instance.idreglement:
            self.fields['date'].initial = datetime.date.today()

        # Mode
        # self.fields["mode"].choices = [(None, "---------")] + [(mode.pk, mode.label) for mode in ModeReglement.objects.all().order_by("label")]

        # Emetteur
        #self.fields["emetteur"].choices = [(None, "---------")] + [(emetteur.pk, emetteur.nom) for emetteur in Emetteur.objects.all().order_by("nom")]

        # Payeur
        self.fields['payeur'].queryset = Payeur.objects.filter(famille_id=idfamille).order_by("nom")
        self.fields['payeur'].widget.attrs.update({"donnees_extra": {"idfamille": idfamille}, "url_ajax": "ajax_modifier_payeur",
                                                   "textes": {"champ": "Nom du payeur", "ajouter": "Saisir un payeur", "modifier": "Modifier un payeur"}})

        # Récupération des infos du dernier règlement saisi
        if not self.instance.idreglement:
            dernier_reglement = Reglement.objects.filter(famille_id=idfamille).last()
            if dernier_reglement:
                self.fields["mode"].initial = dernier_reglement.mode
                self.fields["emetteur"].initial = dernier_reglement.emetteur
                self.fields["payeur"].initial = dernier_reglement.payeur

        # Compte bancaire par défaut
        try:
            compte = CompteBancaire.objects.get(defaut=True)
            if not self.instance.idreglement and compte:
                self.fields["compte"].initial = compte
        except:
            pass

        # Ventilation
        self.fields['ventilation'].label = False

        # Si paiement d'une facture
        if idfacture:
            self.fields["montant"].initial = Facture.objects.get(pk=idfacture).solde_actuel
            self.fields["ventilation"].widget.attrs["idfacture"] = idfacture

        # Si le règlement est déjà inclus dans un dépôt
        if self.instance.depot:
            self.fields['date'].widget.attrs['disabled'] = "disabled"
            self.fields['mode'].widget.attrs['disabled'] = "disabled"
            self.fields['emetteur'].widget.attrs['disabled'] = "disabled"
            self.fields['date_differe'].widget.attrs['disabled'] = "disabled"
            self.fields['numero_piece'].disabled = True
            self.fields['montant'].disabled = True
            self.fields['compte'].disabled = True
            self.fields['date'].required = False
            self.fields['mode'].required = False

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}"),
            Hidden('famille', value=idfamille),
            Fieldset('Généralités',
                Field('date'),
                Field('mode'),
                Field('emetteur'),
                Field('numero_piece'),
                PrependedText('montant', utils_preferences.Get_symbole_monnaie()),
                Field('payeur'),
            ),
            Fieldset('Ventilation',
                Field('ventilation'),
                HTML(EXTRA_HTML),
            ),
            Fieldset('Options',
                Field('observations'),
                Field('numero_quittancier'),
            ),
            Fieldset('Encaissement',
                Field('compte'),
                Field('date_differe'),
            ),
        )
        if self.instance.depot:
            self.helper.layout.insert(1, HTML("""
            <p class='text-orange'><i class='fa fa-exclamation-triangle margin-r-5'></i>
            Certains champs sont protégés contre la modification car ce règlement est déjà inclus dans le dépôt '%s' du %s.</p>
            """ % (self.instance.depot.nom, utils_dates.ConvertDateToFR(self.instance.depot.date))))

    def clean(self):
        # Vérifie qu'un montant a bien été saisi
        if not self.cleaned_data["montant"]:
            self.add_error("montant", "Vous devez saisir un montant")
            return
        return self.cleaned_data

    def clean_mode(self):
        if self.instance and self.instance.depot:
            return getattr(self.instance, "mode")
        return self.cleaned_data["mode"]

    def clean_date(self):
        if self.instance and self.instance.depot:
            return getattr(self.instance, "date")
        return self.cleaned_data["date"]

    def clean_emetteur(self):
        if self.cleaned_data["emetteur"] in ("None", ""):
            self.cleaned_data["emetteur"] = None
        if self.cleaned_data["emetteur"] and self.cleaned_data["emetteur"].mode_id != self.cleaned_data["mode"].pk:
            self.cleaned_data["emetteur"] = None
        if self.instance and self.instance.depot:
            return getattr(self.instance, "emetteur")
        return self.cleaned_data["emetteur"]

    def clean_date_differe(self):
        if self.instance and self.instance.depot:
            return getattr(self.instance, "date_differe")
        return self.cleaned_data["date_differe"]



EXTRA_HTML = """
<div class="input-group" style="margin-bottom: 10px;">
    <div class="input-group-prepend">
        <span id="icone_statut_ventilation" class="input-group-text"><i class="fa fa-check-circle-o"></i></span>
    </div>
    <input id="statut_ventilation" type="text" class="form-control" style="font-weight: bold;" readonly>
    <select id="id_mode_regroupement" title="Mode de regroupement" class="custom-select" style="width: 100px;flex: 0.2;">
        <option value='mois'>Mois</option>
        <option value='facture'>Facture</option>
        <option value='individu'>Individu</option>
        <option value='date'>Date</option>
    </select>
    <span class="input-group-append">
        <button type="button" id="bouton_ventiler_auto" title='Ventiler automatiquement' class="btn btn-default input-group-text"><i class='fa fa-magic'></i></button>
        <button type="button" id="bouton_ventiler_tout" title='Tout ventiler' class="btn btn-default input-group-text"><i class='fa fa-check'></i></button>
        <button type="button" id="bouton_ventiler_rien" title='Tout déventiler' class="btn btn-default input-group-text"><i class='fa fa-remove'></i></button>
    </span>
</div>

<div id="div_table_ventilation" style="height: 350px;margin-bottom: 20px;">
    <table id="table_ventilation" class="table table-bordered noselect">
        <thead>
            <tr>
                <th>Date</th>
                <th>Individu</th>
                <th>Intitulé</th>
                <th style="width: 80px;">N° Facture</th>
                <th style="width: 70px;">Montant</th>
                <th style="width: 70px;">A ventiler</th>
                <th style="width: 70px;">Ventilé</th>
            </tr>
        </thead>
        <tbody>
        </tbody>
    </table>
</div>

<script>
    var idfamille = {{ idfamille|default:0 }};
    var idreglement = {{ reglement.pk|default:0 }};
</script>

"""
