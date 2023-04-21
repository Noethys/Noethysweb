# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, decimal, datetime
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Sum, Count
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Prestation, Reglement, Payeur, Famille, Ventilation
from facturation.forms.solder_impayes import Formulaire


def Solder(request):
    # Récupération des variables
    selections = json.loads(request.POST.get("selections"))
    date_debut = utils_dates.ConvertDateENGtoDate(request.POST.get("date_debut"))
    date_fin = utils_dates.ConvertDateENGtoDate(request.POST.get("date_fin"))

    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        pass

    # Traitement
    for selection in selections:
        montant = decimal.Decimal("%.02f" % selection["2"])
        idfamille = int(selection["3"])

        # Récupération du payeur de la famille
        dernier_reglement = Reglement.objects.select_related("payeur").filter(famille_id=idfamille).last()
        payeur = dernier_reglement.payeur if dernier_reglement else Payeur.objects.create(famille_id=idfamille, nom=Famille.objects.get(pk=idfamille).nom)

        # Création du règlement
        reglement = Reglement.objects.create(famille_id=idfamille, date=datetime.date.today(),
            compte=form.cleaned_data.get("compte", None), mode=form.cleaned_data.get("mode", None), emetteur=form.cleaned_data.get("emetteur", None),
            montant=montant, payeur=payeur, observations="Créé avec la fonction Solder les impayés")

        # Création des ventilations
        prestations = Prestation.objects.filter(famille_id=idfamille, date__gte=date_debut, date__lte=date_fin).distinct().order_by("date")
        ventilations = Ventilation.objects.values("prestation").filter(famille_id=idfamille, prestation__in=prestations).annotate(total=Sum("montant"))
        dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
        liste_ajouts = []
        for prestation in prestations:
            solde_prestation = prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0))
            if solde_prestation:
                liste_ajouts.append(Ventilation(famille_id=idfamille, reglement=reglement, prestation=prestation, montant=solde_prestation))
        Ventilation.objects.bulk_create(liste_ajouts)

    return JsonResponse({"resultat": True})


class View(CustomView, TemplateView):
    menu_code = "solder_impayes"
    template_name = "facturation/solder_impayes.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Solder les impayés"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))

        data = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "data": data,
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])

        # Création des colonnes
        liste_colonnes = ["Famille", "Nbre prestations", "Impayés"]

        # Création des lignes
        familles = Prestation.objects.select_related("famille").values("famille", "famille__nom").filter(date__gte=date_debut, date__lte=date_fin).annotate(nbre_prestations=Count("idprestation"), total_prestations=Sum("montant"), total_ventilation=Sum("ventilation__montant"))

        liste_lignes = []
        for famille in familles:
            impaye = (famille["total_prestations"] or decimal.Decimal(0)) - (famille["total_ventilation"] or decimal.Decimal(0))
            if impaye:
                ligne = {
                    "0": famille["famille__nom"],
                    "1": famille["nbre_prestations"],
                    "2": float(impaye),
                    "3": famille["famille"],
                }
                liste_lignes.append(ligne)

        # Préparation des résultats
        data = {
            "date_debut": date_debut,
            "date_fin": date_fin,
            "periode": parametres["periode"],
            "compte": parametres["compte"].pk if parametres["compte"] else None,
            "mode": parametres["mode"].pk if parametres["mode"] else None,
            "emetteur": parametres["emetteur"].pk if parametres["emetteur"] else None,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
        }
        return data
