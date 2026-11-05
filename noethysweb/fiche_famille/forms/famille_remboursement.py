# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, decimal
from django import forms
from django.forms import ModelForm
from django.db.models import Q, Sum
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Hidden, Fieldset, HTML, Div
from crispy_forms.bootstrap import Field, PrependedText
from core.forms.select2 import Select2Widget
from core.forms.base import FormulaireBase
from core.utils.utils_commandes import Commandes
from core.models import Reglement, ModeReglement, Payeur, CompteBancaire, Prestation
from core.widgets import DatePickerWidget, Select_avec_commandes
from core.utils import utils_preferences
from fiche_famille.widgets import Selection_mode_reglement


def Get_situation_famille(idfamille=None):
    """ Renvoie le total facturé, le total réglé et le crédit remboursable de la famille """
    total_du = Prestation.objects.filter(famille_id=idfamille).aggregate(total=Sum("montant"))["total"] or decimal.Decimal(0)
    total_regle = Reglement.objects.filter(famille_id=idfamille).aggregate(total=Sum("montant"))["total"] or decimal.Decimal(0)
    credit = total_regle - total_du
    return {"total_du": total_du, "total_regle": total_regle, "credit": credit if credit > 0 else decimal.Decimal(0)}


class Formulaire(FormulaireBase, ModelForm):
    date = forms.DateField(label="Date du remboursement", required=True, widget=DatePickerWidget())
    choix_montant = forms.ChoiceField(label="Montant à rembourser", choices=[("total", "Tout le crédit"), ("partiel", "Un autre montant")],
                                      widget=forms.RadioSelect, initial="total", required=True)
    montant = forms.DecimalField(label="Montant", max_digits=6, decimal_places=2, initial=0.0, required=True)
    confirmation_depassement = forms.BooleanField(label="Je confirme vouloir rembourser plus que le crédit disponible", required=False)
    payeur = forms.ModelChoiceField(label="Rembourser à", queryset=Payeur.objects.none(), widget=Select_avec_commandes(), required=True,
                                    help_text="Personne qui reçoit l'argent.")
    mode = forms.ModelChoiceField(label="Mode de remboursement", queryset=ModeReglement.objects.all().order_by("label"), widget=Selection_mode_reglement(), required=True)
    compte = forms.ModelChoiceField(label="Compte bancaire débité", widget=Select2Widget({"data-minimum-input-length": 0}), queryset=CompteBancaire.objects.none(), required=True,
                                    help_text="Compte de la structure d'où part l'argent.")
    observations = forms.CharField(label="Observations", widget=forms.Textarea(attrs={'rows': 2}), required=False,
                                   help_text="Ce commentaire sera enregistré dans le règlement de remboursement.")

    class Meta:
        model = Reglement
        fields = ["famille", "date", "mode", "payeur", "observations", "montant", "compte"]

    def __init__(self, *args, **kwargs):
        idfamille = kwargs.pop("idfamille")
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'famille_remboursement_form'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-3'
        self.helper.field_class = 'col-md-9'

        # Situation de la famille
        self.situation = Get_situation_famille(idfamille)
        self.credit = self.situation["credit"]
        symbole = utils_preferences.Get_symbole_monnaie()

        # Date
        self.fields["date"].initial = datetime.date.today()

        # Montant
        if self.credit > 0:
            self.fields["choix_montant"].choices = [("total", "Tout le crédit (%s)" % Formate_montant_fr(self.credit)), ("partiel", "Un autre montant")]
            self.fields["montant"].initial = self.credit
        else:
            self.fields["choix_montant"].initial = "partiel"

        # Compte bancaire
        self.fields["compte"].queryset = CompteBancaire.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)).order_by("nom")
        try:
            compte = CompteBancaire.objects.get(defaut=True)
            if not self.instance.idreglement and compte:
                self.fields["compte"].initial = compte
        except:
            pass

        # Bénéficiaire (payeur)
        self.fields['payeur'].queryset = Payeur.objects.filter(famille_id=idfamille).order_by("nom")
        self.fields['payeur'].widget.attrs.update({"donnees_extra": {"idfamille": idfamille}, "url_ajax": "ajax_modifier_payeur",
                                                   "textes": {"champ": "Nom du bénéficiaire", "ajouter": "Saisir un bénéficiaire", "modifier": "Modifier un bénéficiaire"}})
        if self.fields['payeur'].queryset.count() == 1:
            self.fields['payeur'].initial = self.fields['payeur'].queryset.first()

        # Affichage
        self.helper.layout = Layout(
            Commandes(annuler_url="{{ view.get_success_url }}", ajouter=False, enregistrer_label="<i class='fa fa-check margin-r-5'></i>Enregistrer le remboursement"),
            Hidden("famille", value=idfamille),
            HTML("{% include 'fiche_famille/famille_remboursement_situation.html' %}"),
            Fieldset("Montant à rembourser",
                Field("choix_montant"),
                PrependedText("montant", symbole),
                Div(
                    HTML("""<div class="alert alert-warning mb-2"><i class="fa fa-exclamation-triangle margin-r-5"></i>
                            Ce montant dépasse le crédit disponible de <b id="remb_depassement">0.00</b>.
                            La famille deviendra débitrice de cette somme.</div>"""),
                    Field("confirmation_depassement"),
                    id="bloc_depassement", css_class="offset-md-3 col-md-9", style="display: none;",
                ),
                Field("date"),
            ),
            Fieldset("Bénéficiaire et modalités",
                Field("payeur"),
                Field("mode"),
                Field("compte"),
                Field("observations"),
            ),
            HTML(RECAPITULATIF),
        )

    def clean(self):
        montant = self.cleaned_data.get("montant")
        if self.cleaned_data.get("choix_montant") == "total" and self.credit > 0:
            montant = self.credit
        if montant is None:
            return self.cleaned_data
        if montant <= 0:
            self.add_error("montant", "Saisissez un montant supérieur à 0.")
            return self.cleaned_data
        if montant > self.credit and not self.cleaned_data.get("confirmation_depassement"):
            self.add_error("confirmation_depassement", "Le montant dépasse le crédit disponible (%s) : cochez cette case pour confirmer." % Formate_montant_fr(self.credit))
            return self.cleaned_data
        # Le remboursement est enregistré comme un règlement négatif
        self.cleaned_data["montant"] = -montant
        return self.cleaned_data


def Formate_montant_fr(montant):
    return "%s %s" % (("%.2f" % montant).replace(".", ","), utils_preferences.Get_symbole_monnaie())


RECAPITULATIF = """
<div class="callout callout-info mt-3" id="remb_recapitulatif">
    <h5><i class="fa fa-list-ul margin-r-5"></i>Ce qui va être enregistré</h5>
    <ul class="mb-0">
        <li>Un règlement négatif de <b id="remb_recap_montant">-</b> dans la liste des règlements de la famille.</li>
        <li>Deux lignes « Remboursement » de même montant (une positive et une négative) dans les prestations. Elles s'annulent et servent uniquement à équilibrer la ventilation.</li>
        <li id="remb_recap_solde">Crédit restant après remboursement : <b id="remb_recap_reste">-</b></li>
    </ul>
</div>
"""
