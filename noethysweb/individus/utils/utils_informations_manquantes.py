# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.db.models import Q
from django.urls import reverse_lazy
from core.models import Quotient, Inscription, Tarif


def Get_informations_manquantes(famille=None, date_reference=None):
    """ Retourne les informations manquantes d'une famille """
    liste_resultats = []

    if not date_reference:
        date_reference = datetime.date.today()

    # Importation des inscriptions
    conditions = Q(famille=famille) & Q(individu__deces=False) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))
    conditions &= (Q(activite__date_fin__isnull=True) | Q(activite__date_fin__gte=date_reference))
    inscriptions = Inscription.objects.filter(conditions)

    if inscriptions:
        # Importation des tarifs des activités concernées
        conditions = Q(methode__icontains="qf") & Q(activite_id__in=list({inscription.activite_id: True for inscription in inscriptions}.keys()))
        conditions &= Q(date_debut__lte=date_reference) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference))
        tarifs = Tarif.objects.filter(conditions).exists()

        if tarifs:
            quotients = Quotient.objects.filter(famille=famille, date_debut__lte=date_reference, date_fin__gte=date_reference).exists()
            if not quotients:
                # Mémorise l'alerte
                liste_resultats.append({
                    "label": "Quotient familial",
                    "valide": False,
                    "titre": "Cliquez ici pour accéder à la page des quotients",
                    "href": reverse_lazy("famille_quotients_liste", kwargs={"idfamille": famille.pk}),
                })

    return liste_resultats
