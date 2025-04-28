# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, decimal
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.shortcuts import render
from django.template import Template, RequestContext
from django.db.models import Max, Q, Sum, Count
from core.models import LotAttestationsFiscales, AttestationFiscale, FiltreListe, Activite, Prestation, Ventilation, Famille, Individu
from core.views.base import CustomView
from core.utils import utils_dates
from facturation.forms.attestations_fiscales_generation import Formulaire


def Modifier_lot_attestations_fiscales(request):
    action = request.POST.get("action")
    idlot = request.POST.get("id")
    nom = request.POST.get("valeur")
    donnees_extra = json.loads(request.POST.get("donnees_extra"))

    # Ajouter un lot
    if action == "ajouter":
        lot = LotAttestationsFiscales.objects.create(nom=nom)
        return JsonResponse({"action": action, "id": lot.pk, "valeur": lot.nom})

    # Modifier un lot
    if action == "modifier":
        lot = LotAttestationsFiscales.objects.get(idlot=int(idlot))
        lot.nom = nom
        lot.save()
        return JsonResponse({"action": action, "id": lot.pk, "valeur": lot.nom})

    # Supprimer un lot
    if action == "supprimer":
        try:
            lot = LotAttestationsFiscales.objects.get(idlot=int(idlot))
            lot.delete()
            return JsonResponse({"action": action, "id": int(idlot)})
        except:
            return JsonResponse({"erreur": "Vous ne pouvez pas supprimer cette donnée"}, status=401)

    return JsonResponse({"erreur": "Erreur !"}, status=401)


def Get_data(cleaned_data=None, selection_prestations=None):
    # Recherche des prestations de la période
    date_debut = utils_dates.ConvertDateENGtoDate(cleaned_data["periode"].split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(cleaned_data["periode"].split(";")[1])

    cleaned_data["activites"] = json.loads(cleaned_data["activites"])
    if cleaned_data["activites"]["type"] == "groupes_activites":
        liste_activites = [activite.pk for activite in Activite.objects.filter(groupes_activites__in=cleaned_data["activites"]["ids"])]
    else:
        liste_activites = cleaned_data["activites"]["ids"]

    idfamille = cleaned_data["famille"] if cleaned_data["selection_familles"] == "FAMILLE" else None

    # Importation des noms d'activités et des dates de naissance
    dict_activites = {activite["pk"]: activite["nom"] for activite in Activite.objects.values("pk", "nom").all()}
    dict_individus = {individu["pk"]: individu["date_naiss"] for individu in Individu.objects.values("pk", "date_naiss").all()}
    dict_familles = {famille["pk"]: famille["nom"] for famille in Famille.objects.values("pk", "nom").all()}

    # Importation des ventilations
    conditions = Q(prestation__date__gte=date_debut) & Q(prestation__date__lte=date_fin)
    if cleaned_data["selection_prestations"] == "ACTIVITES": conditions &= Q(prestation__activite__in=liste_activites)
    if idfamille: conditions &= Q(famille=cleaned_data["famille"])
    if cleaned_data["type_donnee"] == "REGLE_PERIODE": conditions &= Q(reglement__date__gte=date_debut) & Q(reglement__date__lte=date_fin)
    ventilations = Ventilation.objects.values("prestation").filter(conditions).annotate(total=Sum("montant"))
    dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}

    # Importation des prestations
    conditions = Q(individu__isnull=False)
    if cleaned_data["type_donnee"] == "REGLE_PERIODE":
        conditions &= Q(pk__in=list(dict_ventilations.keys()))
    else:
        conditions &= Q(date__gte=date_debut) & Q(date__lte=date_fin)
    if cleaned_data["selection_prestations"] == "ACTIVITES": conditions &= Q(activite__in=liste_activites)
    if selection_prestations != None: conditions &= Q(label__in=selection_prestations.keys())
    if idfamille: conditions &= Q(famille=cleaned_data["famille"])
    liste_prestations = Prestation.objects.values("pk", "label", "montant", "famille_id", "individu_id", "activite_id").filter(conditions).order_by("label")

    return {"activites" : dict_activites, "individus": dict_individus, "familles": dict_familles, "prestations": liste_prestations, "ventilations": dict_ventilations}


def Get_prestations(cleaned_data):
    # Recherche des prestations de la période
    data = Get_data(cleaned_data=cleaned_data)

    # Regroupement des prestations par label
    dict_prestations = {}
    for prestation in data["prestations"]:
        if not cleaned_data["date_naiss_min"] or (data["individus"].get(prestation["individu_id"], None) and data["individus"][prestation["individu_id"]] >= cleaned_data["date_naiss_min"]):
            if prestation["label"] not in dict_prestations:
                dict_prestations[prestation["label"]] = {"activite__nom": data["activites"].get(prestation["activite_id"], ""), "idactivite": prestation["activite_id"], "nbre": 0,
                                                     "total": decimal.Decimal(0), "regle": decimal.Decimal(0), "solde": decimal.Decimal(0)}
            dict_prestations[prestation["label"]]["total"] += prestation["montant"]
            dict_prestations[prestation["label"]]["regle"] += data["ventilations"].get(prestation["pk"], decimal.Decimal(0))
            dict_prestations[prestation["label"]]["solde"] = dict_prestations[prestation["label"]]["total"] - dict_prestations[prestation["label"]]["regle"]
            dict_prestations[prestation["label"]]["nbre"] += 1

    liste_prestations = [{**dict_prestation, **{"label": label}} for label, dict_prestation in dict_prestations.items()]
    return liste_prestations


def Ajuster_attestations_fiscales(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        html = "{% load crispy_forms_tags %} {% crispy form %} {% include 'core/messages.html' %}<script>init_page();</script>"
        data = Template(html).render(RequestContext(request, {"form": form}))
        liste_messages_erreurs = [erreur[0].message for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"html": data, "erreur": "Veuillez corriger les erreurs suivantes : %s." % ", ".join(liste_messages_erreurs)}, status=401)

    liste_prestations = Get_prestations(form.cleaned_data)
    return render(request, "facturation/attestations_fiscales_generation_ajustement.html", {"liste_prestations": liste_prestations})


def Get_attestations_fiscales(cleaned_data={}, selection_prestations={}):
    # Recherche des prestations de la période
    data = Get_data(cleaned_data=cleaned_data, selection_prestations=selection_prestations)

    # Regroupement des prestations par label
    dict_attestations = {}
    for prestation in data["prestations"]:
        if not cleaned_data["date_naiss_min"] or (data["individus"].get(prestation["individu_id"], None) and data["individus"][prestation["individu_id"]] >= cleaned_data["date_naiss_min"]):
            if prestation["famille_id"] not in dict_attestations:
                dict_attestations[prestation["famille_id"]] = {"nom": data["familles"].get(prestation["famille_id"], ""), "individus": {}, "activites": [], "total": decimal.Decimal(0), "regle": decimal.Decimal(0), "solde": decimal.Decimal(0)}
            if prestation["individu_id"] not in dict_attestations[prestation["famille_id"]]["individus"]:
                dict_attestations[prestation["famille_id"]]["individus"][prestation["individu_id"]] = {"total": decimal.Decimal(0), "regle": decimal.Decimal(0), "solde": decimal.Decimal(0)}
            if prestation["activite_id"] not in dict_attestations[prestation["famille_id"]]["activites"]:
                dict_attestations[prestation["famille_id"]]["activites"].append(prestation["activite_id"])

            ajustement = selection_prestations[prestation["label"]]
            total = prestation["montant"] + ajustement # max(prestation["montant"] + ajustement, decimal.Decimal(0))
            regle = data["ventilations"].get(prestation["pk"], decimal.Decimal(0)) + ajustement # max(dict_ventilations.get(prestation["pk"], decimal.Decimal(0)) + ajustement, decimal.Decimal(0))

            dict_attestations[prestation["famille_id"]]["individus"][prestation["individu_id"]]["total"] += total
            dict_attestations[prestation["famille_id"]]["individus"][prestation["individu_id"]]["regle"] += regle
            dict_attestations[prestation["famille_id"]]["individus"][prestation["individu_id"]]["solde"] = dict_attestations[prestation["famille_id"]]["individus"][prestation["individu_id"]]["total"] - dict_attestations[prestation["famille_id"]]["individus"][prestation["individu_id"]]["regle"]

            dict_attestations[prestation["famille_id"]]["total"] += total
            dict_attestations[prestation["famille_id"]]["regle"] += regle
            dict_attestations[prestation["famille_id"]]["solde"] = dict_attestations[prestation["famille_id"]]["total"] - dict_attestations[prestation["famille_id"]]["regle"]

    return dict_attestations


def Recherche_attestations_fiscales(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        html = "{% load crispy_forms_tags %} {% crispy form %} {% include 'core/messages.html' %}<script>init_page();</script>"
        data = Template(html).render(RequestContext(request, {"form": form}))
        liste_messages_erreurs = [erreur[0].message for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"html": data, "erreur": "Veuillez corriger les erreurs suivantes : %s." % ", ".join(liste_messages_erreurs)}, status=401)

    # Récupération des prestations sélectionnées et des ajustements
    selection_prestations = {index_prestation: decimal.Decimal(ajustement) for index_prestation, ajustement in json.loads(request.POST["liste_prestations_json"])}

    # Recherche des attestations fiscales à générer
    dict_attestations_fiscales = Get_attestations_fiscales(cleaned_data=form.cleaned_data, selection_prestations=selection_prestations)
    liste_attestations_fiscales = sorted(dict_attestations_fiscales.items(), key=lambda x: x[1]["nom"])

    return render(request, "facturation/attestations_fiscales_generation_selection.html", {"attestations_fiscales": liste_attestations_fiscales})


def Generation_attestations_fiscales(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"html": "ERREUR!", "erreur": "Veuillez renseigner les paramètres manquants"}, status=401)

    # Récupération de la période
    date_debut = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[0])
    date_fin = utils_dates.ConvertDateENGtoDate(form.cleaned_data["periode"].split(";")[1])

    # Récupération des prestations sélectionnées, des ajustements et des attestations sélectionnées
    selection_prestations = {index_prestation: decimal.Decimal(ajustement) for index_prestation, ajustement in json.loads(request.POST["liste_prestations_json"])}
    selection_attestations_fiscales = json.loads(request.POST["liste_attestations_fiscales_json"])

    if not selection_attestations_fiscales:
        return JsonResponse({"html": "ERREUR!", "erreur": "Vous devez sélectionner au moins une attestation à générer"}, status=401)

    # Prochain numéro
    prochain_numero = int(form.cleaned_data["prochain_numero"])

    # Recherche des attestations fiscales à générer
    dict_attestations_fiscales = Get_attestations_fiscales(cleaned_data=form.cleaned_data, selection_prestations=selection_prestations)
    liste_attestations_fiscales = sorted(dict_attestations_fiscales.items(), key=lambda x: x[1]["nom"])

    liste_attestations_generees = []
    liste_id_attestations = []
    for idfamille, detail in liste_attestations_fiscales:
        if idfamille in selection_attestations_fiscales:
            attestation = AttestationFiscale.objects.create(
                numero=prochain_numero,
                famille_id=idfamille,
                date_edition=form.cleaned_data["date_emission"],
                date_debut=date_debut,
                date_fin=date_fin,
                lot=form.cleaned_data["lot_attestations_fiscales"],
                total=detail["total"] if form.cleaned_data["type_donnee"] == "FACTURE" else detail["regle"],
                activites=detail["activites"],
                individus=list(detail["individus"].keys()),
                detail=json.dumps([{"idindividu": idindividu, "montant": float(detail_individu["total"] if form.cleaned_data["type_donnee"] == "FACTURE" else detail_individu["regle"])} for idindividu, detail_individu in detail["individus"].items()]),
            )
            liste_attestations_generees.append(attestation)
            liste_id_attestations.append(attestation.pk)
            prochain_numero += 1

    # Importation des attestations générées
    id_min, id_max = min(liste_id_attestations), max(liste_id_attestations)
    attestations_fiscales = AttestationFiscale.objects.select_related("famille").filter(pk__gte=id_min, pk__lte=id_max).order_by("idattestation")

    # Enregistre le filtre pour l'impression
    FiltreListe.objects.filter(nom="facturation.views.attestations_fiscales_impression", utilisateur=request.user).delete()
    parametres = """{"champ": "idattestation", "criteres": ["%d", "%d"], "condition": "COMPRIS", "label_filtre": "Attestation fiscale : Dernières attestations fiscales générées"}""" % (id_min, id_max)
    FiltreListe.objects.create(nom="facturation.views.attestations_fiscales_impression", parametres=parametres, utilisateur=request.user)

    # Enregistre le filtre pour l'envoi par email
    FiltreListe.objects.filter(nom="facturation.views.attestations_fiscales_email", utilisateur=request.user).delete()
    parametres = """{"champ": "idattestation", "criteres": ["%d", "%d"], "condition": "COMPRIS", "label_filtre": "Attestation fiscale : Dernières attestations fiscales générées"}""" % (id_min, id_max)
    FiltreListe.objects.create(nom="facturation.views.attestations_fiscales_email", parametres=parametres, utilisateur=request.user)

    return render(request, "facturation/attestations_fiscales_generation_actions.html", {"attestations_fiscales": attestations_fiscales})


class View(CustomView, TemplateView):
    menu_code = "attestations_fiscales_generation"
    template_name = "facturation/attestations_fiscales_generation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Génération des attestations fiscales"
        context['box_titre'] = "Générer un lot d'attestations fiscales"
        context['box_introduction'] = "Veuillez renseigner les paramètres de sélection des attestations fiscales à générer et cliquez sur le bouton Rechercher."
        idfamille = kwargs.get("idfamille", None)
        context['form'] = kwargs.get("form", Formulaire(request=self.request, idfamille=idfamille))
        return context
