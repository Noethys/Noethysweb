# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.db.models import Q, Count, Sum
from core.views import accueil_widget
from core.models import Tarif, Quotient, Prestation, Famille


class Widget(accueil_widget.Widget):
    code = "quotients_manquants"
    label = "Quotients manquants"

    def init_context_data(self):
        self.context["quotients_manquants"] = self.Get_quotients_manquants()

    def Get_quotients_manquants(self):
        resultats = []

        # Période à étudier
        date_debut, date_fin = (datetime.date.today() - datetime.timedelta(days=40), datetime.date.today())

        # Recherche des familles sans quotient
        tarifs = Tarif.objects.filter((Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut)), date_debut__lte=date_fin, methode__icontains="qf").values_list("pk", flat=True).distinct()
        familles_avec_quotients = Quotient.objects.filter(date_debut__lte=date_fin, date_fin__gte=date_debut).values_list("famille_id", flat=True).distinct()
        prestations = Prestation.objects.filter(tarif__in=tarifs, date__gte=date_debut, date__lte=date_fin)
        familles_avec_prestations = prestations.values_list("famille_id", flat=True).distinct()
        familles_sans_quotient = list(Famille.objects.values_list("pk", "nom").filter(pk__in=familles_avec_prestations).exclude(pk__in=familles_avec_quotients).order_by("nom"))
        ids_familles = [idfamille for idfamille, nom_famille in familles_sans_quotient]

        # Détails : nombre de prestations et montant par famille
        stats = {item["famille_id"]: item for item in prestations.filter(famille_id__in=ids_familles).values("famille_id").annotate(nbre=Count("pk"), total=Sum("montant"))}

        # Détails : activités concernées par famille
        activites = {}
        for idfamille, nom_activite in prestations.filter(famille_id__in=ids_familles, activite__isnull=False).values_list("famille_id", "activite__nom").distinct().order_by("activite__nom"):
            activites.setdefault(idfamille, []).append(nom_activite)

        # Détails : état du quotient (aucun, expiré, ou à venir). Aucun de ces quotients ne couvre la période étudiée.
        derniere_fin, prochain_debut = {}, {}
        for idfamille, debut, fin in Quotient.objects.filter(famille_id__in=ids_familles).values_list("famille_id", "date_debut", "date_fin"):
            if fin < date_debut:
                derniere_fin[idfamille] = max(fin, derniere_fin.get(idfamille, fin))
            elif debut > date_fin:
                prochain_debut[idfamille] = min(debut, prochain_debut.get(idfamille, debut))

        # Mise en forme des données
        for idfamille, nom_famille in familles_sans_quotient:
            if idfamille in derniere_fin:
                etat = "Quotient expiré le %s" % derniere_fin[idfamille].strftime("%d/%m/%Y")
            elif idfamille in prochain_debut:
                etat = "Quotient valable à partir du %s" % prochain_debut[idfamille].strftime("%d/%m/%Y")
            else:
                etat = "Aucun quotient enregistré"
            resultats.append({
                "titre": nom_famille, "idfamille": idfamille, "etat": etat,
                "activites": activites.get(idfamille, []),
                "nbre": stats.get(idfamille, {}).get("nbre", 0), "total": stats.get(idfamille, {}).get("total") or 0,
            })

        return resultats
