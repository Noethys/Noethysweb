# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views.base import CustomView
from django.views.generic import TemplateView
from core.utils import utils_dates, utils_dictionnaires
from facturation.utils import utils_rappels
from django.http import JsonResponse
from django.shortcuts import render
from facturation.forms.rappels_generation import Formulaire
from core.models import LotRappels, ModeleRappel, Rappel, FiltreListe, Activite, Prestation
from django.template import Template, RequestContext
from django.db.models import Max
import json, datetime




def Modifier_lot_rappels(request):
    action = request.POST.get("action")
    idlot = request.POST.get("id")
    nom = request.POST.get("valeur")
    donnees_extra = json.loads(request.POST.get("donnees_extra"))

    # Ajouter un lot
    if action == "ajouter":
        lot = LotRappels.objects.create(nom=nom)
        return JsonResponse({"action": action, "id": lot.pk, "valeur": lot.nom})

    # Modifier un lot
    if action == "modifier":
        lot = LotRappels.objects.get(idlot=int(idlot))
        lot.nom = nom
        lot.save()
        return JsonResponse({"action": action, "id": lot.pk, "valeur": lot.nom})

    # Supprimer un lot
    if action == "supprimer":
        try:
            lot = LotRappels.objects.get(idlot=int(idlot))
            lot.delete()
            return JsonResponse({"action": action, "id": int(idlot)})
        except:
            return JsonResponse({"erreur": "Vous ne pouvez pas supprimer cette donnée"}, status=401)

    return JsonResponse({"erreur": "Erreur !"}, status=401)


def Get_rappels(data={}):
    # Sélection familles
    selection_familles = None
    if data["selection_familles"] == "FAMILLE":
        selection_familles = {"filtre": "FAMILLE", "famille": data["famille"]}
    if data["selection_familles"] == "SANS_PRESTATION":
        date_debut = utils_dates.ConvertDateENGtoDate(data["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(data["periode"].split(";")[1])
        selection_familles = {"filtre": "SANS_PRESTATION", "date_debut": date_debut, "date_fin": date_fin}
    if data["selection_familles"] == "ABSENT_LOT_FACTURES":
        selection_familles = {"filtre": "ABSENT_LOT_FACTURES", "lot_factures": data["lot_factures"]}

    # Activités
    data["activites"] = json.loads(data["activites"])
    if data["activites"]["type"] == "groupes_activites":
        liste_activites = [activite.pk for activite in Activite.objects.filter(groupes_activites__in=data["activites"]["ids"])]
    else:
        liste_activites = data["activites"]["ids"]

    # Calcul des rappels
    facturation = utils_rappels.Facturation()
    dict_rappels = facturation.GetDonnees(liste_activites=liste_activites, date_reference=data["date_reference"], date_edition=data["date_emission"],
                                            categories_prestations=data["categories"], selection_familles=selection_familles)
    liste_rappels = facturation.GetListeTriee(dict_rappels)
    return liste_rappels



def Recherche_rappels(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        html = "{% load crispy_forms_tags %} {% crispy form %} {% include 'core/messages.html' %}<script>init_page();</script>"
        data = Template(html).render(RequestContext(request, {"form": form}))
        liste_messages_erreurs = [erreur[0].message for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"html": data, "erreur": "Veuillez corriger les erreurs suivantes : %s." % ", ".join(liste_messages_erreurs)}, status=401)

    # Recherche des rappels à générer
    liste_rappels = Get_rappels(form.cleaned_data)

    # Importation des modèles de rappel
    liste_modeles = ModeleRappel.objects.all()
    return render(request, "facturation/rappels_generation_selection.html", {"rappels": liste_rappels, "modeles": liste_modeles})



def Generation_rappels(request):
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"html": "ERREUR!", "erreur": "Veuillez renseigner les paramètres manquants"}, status=401)

    liste_rappels_coches = json.loads(request.POST.get("liste_rappels_json"))
    dict_rappels_coches = {}
    for idfamille, idtexte in liste_rappels_coches:
        if not idtexte:
            return JsonResponse({"html": "ERREUR!", "erreur": "Vous devez sélectionner un texte de rappel pour chaque ligne cochée"}, status=401)
        dict_rappels_coches[int(idfamille)] = int(idtexte)

    # Recherche des factures à générer
    liste_rappels = Get_rappels(form.cleaned_data)

    # Recherche le prochain numéro de facture
    numero = (Rappel.objects.filter().aggregate(Max('numero')))['numero__max']
    if not numero: numero = 0
    numero += 1

    liste_rappels_generes = []
    liste_id_rappels = []
    for dict_rappel in liste_rappels:
        IDfamille = dict_rappel["IDfamille"]
        if IDfamille in dict_rappels_coches:
            rappel = Rappel.objects.create(
                numero=numero,
                famille_id=IDfamille,
                date_edition=form.cleaned_data["date_emission"],
                activites=";".join([str(x) for x in dict_rappel["liste_activites"]])[:200],
                modele_id=dict_rappels_coches[IDfamille],
                date_reference=form.cleaned_data["date_reference"],
                solde=dict_rappel["solde_num"],
                lot=form.cleaned_data["lot_rappels"],
                date_min=dict_rappel["date_min"],
                date_max=dict_rappel["date_max"],
                prestations=";".join(form.cleaned_data["categories"]),
            )
            liste_rappels_generes.append(rappel)
            liste_id_rappels.append(rappel.pk)
            numero += 1

    # Importation des rappels générés
    id_min, id_max = min(liste_id_rappels), max(liste_id_rappels)
    rappels = Rappel.objects.select_related('famille').filter(pk__gte=id_min, pk__lte=id_max).order_by("idrappel")

    # Enregistre le filtre pour l'impression
    FiltreListe.objects.filter(nom="facturation.views.rappels_impression", utilisateur=request.user).delete()
    parametres = """{"champ": "idrappel", "criteres": ["%d", "%d"], "condition": "COMPRIS", "label_filtre": "Rappel : Derniers rappels générés"}""" % (id_min, id_max)
    FiltreListe.objects.create(nom="facturation.views.rappels_impression", parametres=parametres, utilisateur=request.user)

    # Enregistre le filtre pour l'envoi par email
    FiltreListe.objects.filter(nom="facturation.views.rappels_email", utilisateur=request.user).delete()
    parametres = """{"champ": "idrappel", "criteres": ["%d", "%d"], "condition": "COMPRIS", "label_filtre": "Rappel : Derniers rappels générés"}""" % (id_min, id_max)
    FiltreListe.objects.create(nom="facturation.views.rappels_email", parametres=parametres, utilisateur=request.user)

    return render(request, "facturation/rappels_generation_actions.html", {"rappels": rappels})




class View(CustomView, TemplateView):
    menu_code = "rappels_generation"
    template_name = "facturation/rappels_generation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Génération des lettres de rappel"
        context['box_titre'] = "Générer un lot de lettres de rappel"
        context['box_introduction'] = "Veuillez renseigner les paramètres de sélection des lettres de rappel à générer et cliquez sur le bouton Rechercher."
        idfamille = kwargs.get("idfamille", None)
        context['form'] = kwargs.get("form", Formulaire(request=self.request, idfamille=idfamille))
        return context

