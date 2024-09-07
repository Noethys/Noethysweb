# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime, copy, uuid
from dateutil import relativedelta
from operator import itemgetter
from colorhash import ColorHash
from django import forms
from django.http import JsonResponse
from django.db.models import Q
from django.template import Template, RequestContext
from django.utils.safestring import mark_safe
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML, ButtonHolder, Hidden
from crispy_forms.bootstrap import Field, Div
from core.forms.select2 import Select2Widget
from core.widgets import DatePickerWidget
from core.forms.base import FormulaireBase
from core.models import Famille, Tarif, Inscription
from core.utils import utils_dates, utils_texte


def Creation_forfait(request):
    # Validation des données saisies
    if not request.POST["idfamille"]: return JsonResponse({"erreur": "Vous devez sélectionner une famille"}, status=401)
    if not request.POST["date_debut"]: return JsonResponse({"erreur": "La date de début semble erronée"}, status=401)
    if not request.POST["date_fin"]: return JsonResponse({"erreur": "La date de fin semble erronée"}, status=401)
    if not request.POST["forfait"]: return JsonResponse({"erreur": "Vous devez sélectionner un forfait dans la liste proposée"}, status=401)
    if not request.POST["date_fin"]: return JsonResponse({"erreur": "La date de la prestation semble erronée"}, status=401)
    if not request.POST["label"]: return JsonResponse({"erreur": "Vous devez saisir un label pour cette prestation"}, status=401)
    if not request.POST["montant"]: return JsonResponse({"erreur": "Vous devez saisir un montant pour cette prestation"}, status=401)

    # Création de la prestation
    if request.POST.get("idprestation", None):
        idprestation = request.POST["idprestation"]
    else:
        idprestation = uuid.uuid4()
    dict_forfait = json.loads(request.POST["dict_forfait"])
    tarif = Tarif.objects.get(pk=dict_forfait["tarif"])
    dict_prestation = {
        "date": str(utils_dates.ConvertDateFRtoDate(request.POST["date"])),
        "categorie": "consommation",
        "label": request.POST["label"],
        "montant_initial": float(request.POST["montant"]),
        "montant": float(request.POST["montant"]),
        "activite": int(dict_forfait["activite"]),
        "tarif": dict_forfait["tarif"],
        "facture": None,
        "famille": int(dict_forfait["famille"]),
        "individu": dict_forfait["individu"],
        "categorie_tarif": dict_forfait["categorie_tarif"],
        "temps_facture": utils_dates.DeltaEnStr(dict_forfait["temps_facture"], separateur=":"),
        "quantite": dict_forfait["quantite"] or 1,
        "tarif_ligne": dict_forfait["tarif_ligne"],
        "tva": float(tarif.tva) if tarif.tva else None,
        "code_compta": tarif.code_compta,
        "aides": [],
        "forfait_date_debut": str(utils_dates.ConvertDateFRtoDate(request.POST["date_debut"]) if request.POST["date_debut"] else None),
        "forfait_date_fin": str(utils_dates.ConvertDateFRtoDate(request.POST["date_fin"]) if request.POST["date_fin"] else None),
        "couleur": ColorHash(str(idprestation)).hex,
    }
    return JsonResponse({"idprestation": idprestation, "dict_prestation": mark_safe(json.dumps(dict_prestation))})


def Get_familles(request):
    """ Renvoie une liste de familles pour le Select2 """
    recherche = request.GET.get("term", "")
    liste_familles = []
    for famille in Famille.objects.all().filter(nom__icontains=recherche).distinct().order_by("nom"):
        liste_familles.append({"id": famille.pk, "text": famille.nom})
    return JsonResponse({"results": liste_familles, "pagination": {"more": True}})


def Get_forfaits_disponibles(request):
    idfamille = request.POST["idfamille"]
    activite = request.POST["activite"]
    selection = request.POST["selection"]
    liste_idinscription = json.loads(request.POST.get("liste_idinscription"))
    date_debut = utils_dates.ConvertDateFRtoDate(request.POST.get("date_debut"))

    liste_forfaits = []
    dict_forfaits = {}

    if date_debut and activite:

        # Importation des inscriptions de cette famille
        inscriptions = Inscription.objects.select_related("individu").filter(famille_id=idfamille, pk__in=liste_idinscription)

        # Recherche de tarifs CREDIT disponibles
        from consommations.views.grille import Facturation
        facturation = Facturation()
        tarifs = Tarif.objects.select_related("nom_tarif").prefetch_related("groupes").filter((Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut)), date_debut__lte=date_debut, activite_id=activite, type="CREDIT")
        for tarif in tarifs:

            # Recherche de la date de facturation
            date_facturation = date_debut
            if tarif.date_facturation == "date_saisie": date_facturation = datetime.date.today()
            elif tarif.date_facturation == "date_debut_activite": date_facturation = activite.date_debut
            elif tarif.date_facturation and tarif.date_facturation.startswith("date:"): date_facturation = utils_dates.ConvertDateENGtoDate(tarif.date_facturation[5:])

            # Calcul de la date de fin du forfait
            date_fin = None
            if tarif.forfait_duree:
                jours, mois, annees = tarif.forfait_duree.split("-")
                jours, mois, annees = int(jours[1:])-1, int(mois[1:]), int(annees[1:])
                date_fin = copy.copy(date_debut)
                if jours: date_fin = date_fin + relativedelta.relativedelta(days=+jours)
                if mois: date_fin = date_fin + relativedelta.relativedelta(months=+mois)
                if annees: date_fin = date_fin + relativedelta.relativedelta(years=+annees)

            resultat = facturation.Calcule_tarif(tarif=tarif, case_tableau={"date": date_debut, "famille": idfamille})
            if resultat:
                montant_tarif, nom_tarif, temps_facture, quantite, tarif_ligne = resultat
                detail_forfait = {"date_fin": utils_dates.ConvertDateToFR(date_fin), "label": nom_tarif, "montant": float(montant_tarif),
                                  "date": utils_dates.ConvertDateToFR(date_facturation), "tarif_ligne": tarif_ligne.pk, "individu": None, "categorie_tarif": None,
                                  "temps_facture": temps_facture, "quantite": quantite, "tarif": tarif.pk, "famille": idfamille, "activite": activite}
                if tarif.forfait_beneficiaire == "famille":
                    key = "0_%d" % tarif.pk
                    liste_forfaits.append((key, "Forfait famille - %s - %s" % (tarif.description or tarif.nom_tarif.nom, utils_texte.Formate_montant(montant_tarif))))
                    dict_forfaits[key] = detail_forfait
                else:
                    for inscription in inscriptions:
                        if not tarif.groupes.all() or inscription.groupe in tarif.groupes.all():
                            key = "%s_%d" % (inscription.individu_id, tarif.pk)
                            liste_forfaits.append((key, "%s - %s - %s" % (inscription.individu.Get_nom(), tarif.description or tarif.nom_tarif.nom, utils_texte.Formate_montant(montant_tarif))))
                            dict_forfaits[key] = copy.copy(detail_forfait)
                            dict_forfaits[key]["individu"] = inscription.individu_id
                            dict_forfaits[key]["categorie_tarif"] = inscription.categorie_tarif_id

    liste_forfaits = sorted(liste_forfaits, key=itemgetter(1))

    # Création des choix du ctrl
    html = """
    <option value="">---------</option>
    {% for key, label in liste_forfaits %}
        <option value="{{ key }}" {% if selection == key %}selected{% endif %}>{{ label }}</option>
    {% endfor %}
    """
    context = {"liste_forfaits": liste_forfaits, "selection": selection}
    html_ctrl = Template(html).render(RequestContext(request, context))

    return JsonResponse({"html_ctrl": html_ctrl, "dict_forfaits": json.dumps(dict_forfaits)})


class Formulaire(FormulaireBase, forms.Form):
    famille = forms.ChoiceField(label="Famille", widget=Select2Widget(), choices=[], required=True)
    date_debut = forms.DateField(label="Du", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    date_fin = forms.DateField(label="Au", required=False, widget=DatePickerWidget(attrs={'afficher_fleches': False}))
    forfait = forms.ChoiceField(label="Forfait", choices=[], initial="aucun", required=False)
    label = forms.CharField(label="Label", required=False)
    date_prestation = forms.DateField(label="Date", widget=DatePickerWidget(attrs={'afficher_fleches': False}), required=False)
    montant = forms.DecimalField(label="Montant", max_digits=6, decimal_places=2, initial=0.0, required=False)

    def __init__(self, *args, **kwargs):
        inscriptions = kwargs.pop("inscriptions", [])
        is_portail = kwargs.pop("is_portail", False)
        super(Formulaire, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'grille_forfaits'
        self.helper.form_method = 'post'

        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-10'

        if inscriptions:
            liste_familles = [(nom, id) for id, nom in {inscription.famille_id: inscription.famille.nom for inscription in inscriptions}.items()]
            liste_familles.sort()
            self.fields["famille"].choices = [(id, nom) for nom, id in liste_familles]

        if is_portail:
            self.fields["date_fin"].disabled = True
            self.fields["label"].disabled = True
            self.fields["date_prestation"].disabled = True
            self.fields["montant"].disabled = True

        self.helper.layout = Layout(
            Hidden("idprestation", value=""),
            Fieldset("Paramètres",
                Field("famille"),
                Field("date_debut"),
                Field("date_fin"),
            ),
            Fieldset("Sélection du forfait",
                Field("forfait"),
            ),
            Fieldset("Prestation",
                Field("label"),
                Field("date_prestation"),
                Field("montant"),
            ),
            ButtonHolder(
                Div(
                    Submit('submit', 'Valider', css_class='btn-primary'),
                    HTML("""<button type="button" class="btn btn-danger" data-dismiss="modal"><i class='fa fa-ban margin-r-5'></i>Annuler</button>"""),
                    css_class="modal-footer", style="padding-bottom:0px;padding-right:0px;"),
            ),
        )

    def clean(self):
        if not self.cleaned_data["date_debut"]:
            self.add_error('date_debut', "Vous devez sélectionner une date de début")
            return
        if not self.cleaned_data["date_fin"]:
            self.add_error('date_fin', "Vous devez sélectionner une date de fin")
            return
        if self.cleaned_data["date_debut"] > self.cleaned_data["date_fin"]:
            self.add_error('date_fin', "La date de fin doit être supérieure à la date de début")
            return
        if not self.cleaned_data["forfait"]:
            self.add_error("forfait", "Vous devez sélectionner un forfait")
            return
        if not self.cleaned_data["label"]:
            self.add_error("label", "Vous devez saisir un label pour la prestation")
            return
        if not self.cleaned_data["date_prestation"]:
            self.add_error("date_prestation", "Vous devez saisir une date pour la prestation")
            return
        if not self.cleaned_data["montant"]:
            self.add_error("montant", "Vous devez saisir un montant pour la prestation")
            return
        return self.cleaned_data
