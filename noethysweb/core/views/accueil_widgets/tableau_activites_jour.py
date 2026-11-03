# -*- coding: utf-8 -*-

import datetime

from django.db.models import Q

from core.models import Activite, Consommation, Inscription, Ouverture
from core.views import accueil_widget


class Widget(accueil_widget.Widget):
    code = "tableau_activites_jour"
    label = "Tableau enfants × activités du jour"

    PRIORITE_ETATS = {
        "present": 60,
        "absentj": 50,
        "absenti": 50,
        "reservation": 40,
        "attente": 30,
        "demande": 20,
        "refus": 10,
    }

    AFFICHAGE_ETATS = {
        "present": ("✓", "Présent", "present"),
        "reservation": ("•", "Réservé / à pointer", "reservation"),
        "absentj": ("AJ", "Absent justifié", "absentj"),
        "absenti": ("A", "Absent injustifié", "absenti"),
        "attente": ("?", "En attente", "attente"),
        "demande": ("D", "Demande", "demande"),
        "refus": ("×", "Refus", "refus"),
    }

    def init_context_data(self):
        date_jour = datetime.date.today()
        structures = self.request.user.structures.all()

        # Ne conserver que les activités réellement ouvertes aujourd'hui.
        ids_activites = list(
            Ouverture.objects.filter(
                date=date_jour,
                activite__structure__in=structures,
            )
            .values_list("activite_id", flat=True)
            .distinct()
        )

        activites = list(
            Activite.objects.filter(pk__in=ids_activites)
            .order_by("nom")
        )

        if not activites:
            self.context["tableau_activites_date"] = date_jour
            self.context["tableau_activites_activites"] = []
            self.context["tableau_activites_lignes"] = []
            return

        # Tous les enfants dont l'inscription est active aujourd'hui dans une
        # des activités affichées. Le widget ne dépend donc pas de l'existence
        # préalable d'une consommation/réservation.
        inscriptions = list(
            Inscription.objects.filter(
                activite_id__in=ids_activites,
                statut="ok",
                date_debut__lte=date_jour,
            )
            .filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_jour))
            .select_related("individu", "activite")
            .order_by("individu__nom", "individu__prenom", "activite__nom")
        )

        individus = {}
        for inscription in inscriptions:
            if not inscription.individu_id:
                continue
            ligne = individus.setdefault(
                inscription.individu_id,
                {
                    "individu": inscription.individu,
                    "activites": set(),
                    "etats": {},
                },
            )
            ligne["activites"].add(inscription.activite_id)

        # Superposer l'état réel du jour lorsqu'une consommation existe.
        consommations = (
            Consommation.objects.filter(
                date=date_jour,
                activite_id__in=ids_activites,
                individu_id__in=list(individus.keys()),
            )
            .select_related("individu", "activite")
            .order_by("individu__nom", "individu__prenom", "activite__nom")
        )

        for conso in consommations:
            ligne = individus.get(conso.individu_id)
            if not ligne:
                continue
            ancien = ligne["etats"].get(conso.activite_id)
            if (
                ancien is None
                or self.PRIORITE_ETATS.get(conso.etat, 0)
                > self.PRIORITE_ETATS.get(ancien, 0)
            ):
                ligne["etats"][conso.activite_id] = conso.etat

        lignes = []
        for ligne in individus.values():
            cellules = []
            for activite in activites:
                concerne = activite.pk in ligne["activites"]
                etat = ligne["etats"].get(activite.pk)

                if not concerne:
                    symbole, libelle, classe = "—", "Non inscrit", "hors-activite"
                elif etat:
                    symbole, libelle, classe = self.AFFICHAGE_ETATS.get(
                        etat, ("?", etat, "autre")
                    )
                else:
                    # Inscrit à l'activité mais sans consommation aujourd'hui.
                    symbole, libelle, classe = "○", "Inscrit - aucune réservation", "inscrit"

                cellules.append(
                    {
                        "activite": activite,
                        "concerne": concerne,
                        "etat": etat,
                        "symbole": symbole,
                        "libelle": libelle,
                        "classe": classe,
                    }
                )

            lignes.append(
                {
                    "individu": ligne["individu"],
                    "cellules": cellules,
                }
            )

        lignes.sort(
            key=lambda item: (
                (item["individu"].nom or "").lower(),
                (item["individu"].prenom or "").lower(),
            )
        )

        self.context["tableau_activites_date"] = date_jour
        self.context["tableau_activites_activites"] = activites
        self.context["tableau_activites_lignes"] = lignes
