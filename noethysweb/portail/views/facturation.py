# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, decimal, datetime, json
logger = logging.getLogger(__name__)
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from django.shortcuts import render
from django.db.models import Sum
from django.contrib import messages
from portail.views.base import CustomView
from core.models import Facture, Prestation, Ventilation, PortailPeriode, Paiement, Reglement, ModeleImpression, Mandat
from core.utils import utils_portail, utils_texte
from portail.utils import paiements
from portail.utils.paiements import commun


class View_retour_paiement(CustomView, TemplateView):
    menu_code = "portail_facturation"
    template_name = "portail/retour_paiement.html"
    etat = None

    def get_context_data(self, **kwargs):
        context = super(View_retour_paiement, self).get_context_data(**kwargs)
        context['page_titre'] = _("Facturation")
        context['etat'] = self.etat
        return context


def effectuer_paiement_en_ligne(request):
    """ Création d'un paiement en ligne. La logique propre à chaque système est dans portail/utils/paiements/ """
    parametres_portail = utils_portail.Get_dict_parametres()

    # Contrôle de la demande envoyée par le navigateur
    demande, erreur = commun.Valider_demande(request=request, parametres_portail=parametres_portail)
    if erreur:
        return erreur

    # Transmission au système de paiement sélectionné dans les paramètres du portail
    systeme = paiements.Get_systeme(parametres_portail.get("paiement_ligne_systeme"))
    if not systeme:
        return commun.Erreur(_("Le paiement en ligne n'est pas activé."))
    return systeme.Creer_paiement(request=request, demande=demande, parametres_portail=parametres_portail)


def get_detail_facture(request):
    """ Génére un texte HTML contenant le détail d'une facture """
    idfacture = int(request.POST.get("idfacture", 0))

    # Importation de la facture
    facture = Facture.objects.filter(pk=idfacture, famille=request.user.famille).first()
    if not facture or not utils_portail.Get_parametre(code="facturation_autoriser_detail_facture"):
        return JsonResponse({"texte": "Accès interdit"}, status=401)

    # Importation des prestations
    prestations = Prestation.objects.select_related("individu", "activite").filter(facture=facture).order_by("date")

    # Création du texte HTML
    context = {
        "facture": facture,
        "prestations": prestations,
        "parametres_portail": utils_portail.Get_dict_parametres(),
    }
    return render(request, 'portail/detail_facture.html', context)


def imprimer_facture(request):
    """ Imprimer une facture au format PDF """
    idfacture = int(request.POST.get("idfacture", 0))

    # Vérifie que le téléchargement est autorisé et que la facture appartient à la famille connectée
    parametres_portail = utils_portail.Get_dict_parametres()
    idmodele_impression = parametres_portail.get("facturation_modele_impression_facture")
    if not parametres_portail.get("facturation_autoriser_telechargement_facture") or not idmodele_impression or not Facture.objects.filter(pk=idfacture, famille=request.user.famille).exists():
        return JsonResponse({"erreur": "Accès interdit"}, status=401)

    # Importation des options d'impression
    modele_impression = ModeleImpression.objects.get(pk=int(idmodele_impression))
    dict_options = json.loads(modele_impression.options)
    dict_options["modele"] = modele_impression.modele_document

    # Création du PDF
    from facturation.utils import utils_facturation
    facturation = utils_facturation.Facturation()
    resultat = facturation.Impression(liste_factures=[idfacture,], dict_options=dict_options)

    return JsonResponse({"nom_fichier": resultat["nom_fichier"]})


class View(CustomView, TemplateView):
    menu_code = "portail_facturation"
    template_name = "portail/facturation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Facturation"

        # Vérifie si la famille est abonnée au prélèvement automatique
        context["prelevement_actif"] = Mandat.objects.filter(famille=self.request.user.famille, actif=True).exists()
        context['paiement_actif'] = not (context['parametres_portail']["paiement_ligne_off_si_prelevement"] and context["prelevement_actif"])

        # Importation des paiements PAYFIP en cours
        context['liste_paiements'] = Paiement.objects.filter(famille=self.request.user.famille, systeme_paiement__in=("payfip", "helloasso"), resultat__isnull=True, horodatage__gt=datetime.datetime.now() - datetime.timedelta(minutes=5))
        dict_paiements = {"F": {}, "P": {}, "C": {}}
        for paiement in context['liste_paiements']:
            for texte in paiement.ventilation.split(","):
                type_impaye = texte[0]
                ID, montant = texte[1:].split("#")
                ID, montant = int(ID), decimal.Decimal(montant)
                dict_paiements[type_impaye].setdefault(ID, decimal.Decimal(0))
                dict_paiements[type_impaye][ID] += montant

        # Affichage des notifications de paiements récents
        for paiement in Paiement.objects.filter(famille=self.request.user.famille, notification__isnull=True, horodatage__gt=datetime.datetime.now() - datetime.timedelta(hours=1)):
            if paiement.resultat == "PAID":
                messages.add_message(self.request, messages.SUCCESS, "Le paiement en ligne de %.2f Euros a été enregistré avec succès" % paiement.montant)
            elif paiement.resultat == "DENIED":
                messages.add_message(self.request, messages.ERROR, "Le paiement en ligne de %.2f Euros a été refusé" % paiement.montant)
            elif paiement.resultat == "CANCELLED":
                messages.add_message(self.request, messages.ERROR, "Le paiement en ligne de %.2f Euros a été annulé" % paiement.montant)
            else:
                messages.add_message(self.request, messages.ERROR, "Le paiement en ligne de %.2f Euros a rencontré une erreur. La notification de paiement semble absente." % paiement.montant)
            paiement.notification = datetime.datetime.now()
            paiement.save()

        # Importation des factures impayées
        liste_factures = []
        liste_factures_impayees = []
        total_factures_impayees = decimal.Decimal(0)
        for facture in Facture.objects.filter(famille=self.request.user.famille).exclude(etat="annulation").order_by("-date_edition"):
            if facture.pk in dict_paiements["F"]:
                facture.regle = facture.total
                facture.solde_actuel = decimal.Decimal(0)
            if facture.solde_actuel and (not facture.date_limite_paiement or datetime.date.today() <= facture.date_limite_paiement):
                liste_factures_impayees.append(facture)
                total_factures_impayees += facture.solde_actuel
            liste_factures.append(facture)
        context['liste_factures_impayees'] = liste_factures_impayees
        context['liste_factures'] = liste_factures

        # Importation de la préfacturation des périodes
        total_periodes_impayees = decimal.Decimal(0)
        liste_finale_periodes = []

        # Récupération des périodes de réservations
        liste_dates_extremes = []
        liste_periodes = []
        for periode in PortailPeriode.objects.select_related("activite").prefetch_related("categories").filter(prefacturation=True):
            if periode.Is_famille_authorized(famille=self.request.user.famille):
                periode.total = decimal.Decimal(0)
                periode.regle = decimal.Decimal(0)
                periode.solde = decimal.Decimal(0)
                liste_periodes.append(periode)
                liste_dates_extremes.append(periode.date_debut)
                liste_dates_extremes.append(periode.date_fin)
        if liste_periodes:
            date_min = min(liste_dates_extremes)
            date_max = max(liste_dates_extremes)

            # Recherche les impayés par période de réservations
            if liste_periodes:
                ventilations = Ventilation.objects.values("prestation").filter(famille=self.request.user.famille, prestation__date__gte=date_min, prestation__date__lte=date_max).annotate(total=Sum("montant"))
                dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
                for prestation in Prestation.objects.filter(famille=self.request.user.famille, date__gte=date_min, date__lte=date_max, facture__isnull=True):
                    solde_prestation = prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0))
                    if solde_prestation > decimal.Decimal(0):
                        for periode in liste_periodes:
                            if periode.date_debut <= prestation.date <= periode.date_fin and prestation.activite_id == periode.activite_id:
                                periode.total += prestation.montant
                                periode.regle += dict_ventilations.get(prestation.pk, decimal.Decimal(0))
                                periode.solde += solde_prestation

                # Ajoute les paiements en cours
                for periode in liste_periodes:
                    if periode.pk in dict_paiements["P"]:
                        periode.regle = periode.total
                        periode.solde = decimal.Decimal(0)
                    total_periodes_impayees += periode.solde
                    if periode.solde:
                        liste_finale_periodes.append(periode)

        context["liste_periodes_prefacturation"] = liste_finale_periodes

        # Importation de la préfacturation des cotisations
        total_cotisations_impayees = decimal.Decimal(0)
        liste_finale_cotisations = []

        ventilations = Ventilation.objects.values("prestation").filter(famille=self.request.user.famille, prestation__cotisation__isnull=False).annotate(total=Sum("montant"))
        dict_ventilations = {ventilation["prestation"]: ventilation["total"] for ventilation in ventilations}
        for prestation in Prestation.objects.select_related("cotisation").filter(famille=self.request.user.famille, cotisation__isnull=False, facture__isnull=True, cotisation__unite_cotisation__prefacturation=True):
            solde_prestation = prestation.montant - dict_ventilations.get(prestation.pk, decimal.Decimal(0))
            if solde_prestation > decimal.Decimal(0):
                prestation.total = prestation.montant
                prestation.regle = dict_ventilations.get(prestation.pk, decimal.Decimal(0))
                prestation.solde = solde_prestation

                # Ajoute les paiements en cours
                if prestation.pk in dict_paiements["C"]:
                    prestation.regle = prestation.total
                    prestation.solde = decimal.Decimal(0)
                total_cotisations_impayees += prestation.solde
                if prestation.solde:
                    liste_finale_cotisations.append(prestation)

        context["liste_cotisations_prefacturation"] = liste_finale_cotisations

        # Création du texte de rappel des impayés
        liste_impayes = []
        texte_impayes = None
        if liste_factures_impayees:
            liste_impayes.append(_("1 facture à régler") if len(liste_factures_impayees) == 1 else _("%d factures à régler") % len(liste_factures_impayees))
        if liste_finale_periodes or liste_finale_cotisations:
            liste_impayes.append(_("des prestations à régler en avance"))
        if liste_impayes:
            texte_impayes = {
                "texte": utils_texte.Convert_liste_to_texte_virgules(liste_impayes),
                "montant": utils_texte.Formate_montant(total_factures_impayees + total_periodes_impayees + total_cotisations_impayees),
            }
        context["texte_impayes"] = texte_impayes

        # Calcul du solde
        if context["parametres_portail"].get("facturation_afficher_solde_famille", False):
            total_prestations = Prestation.objects.values('famille_id').filter(famille=self.request.user.famille).aggregate(total=Sum("montant"))
            total_reglements = Reglement.objects.values('famille_id').filter(famille=self.request.user.famille).aggregate(total=Sum("montant"))
            total_du = total_prestations["total"] if total_prestations["total"] else decimal.Decimal(0)
            total_regle = total_reglements["total"] if total_reglements["total"] else decimal.Decimal(0)
            context["solde_famille"] = total_du - total_regle

        return context
