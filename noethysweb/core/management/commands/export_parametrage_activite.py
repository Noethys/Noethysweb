# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Export du paramétrage d'une ou plusieurs activités au format JSON, en vue d'une analyse par une IA.
Même export que la page Paramétrage > Activités > Contrôle IA du paramétrage.

Exemples :
    python manage.py export_parametrage_activite --liste
    python manage.py export_parametrage_activite 12
    python manage.py export_parametrage_activite 12 15 --depuis 2025-09-01 --jusqua 2026-08-31
    python manage.py export_parametrage_activite --toutes --sortie /tmp/exports
"""

import os, datetime
from django.core.management.base import BaseCommand, CommandError
from core.models import Activite
from core.utils import utils_export_parametrage


class Command(BaseCommand):
    help = "Exporte le paramétrage d'activités au format JSON (sans données personnelles des familles)"

    def add_arguments(self, parser):
        parser.add_argument("idactivites", nargs="*", type=int, help="ID des activités à exporter")
        parser.add_argument("--toutes", action="store_true", help="Exporter toutes les activités")
        parser.add_argument("--liste", action="store_true", help="Afficher la liste des activités et quitter")
        parser.add_argument("--depuis", type=datetime.date.fromisoformat, help="Début de la période analysée (AAAA-MM-JJ)")
        parser.add_argument("--jusqua", type=datetime.date.fromisoformat, help="Fin de la période analysée (AAAA-MM-JJ)")
        parser.add_argument("--sortie", default=".", help="Répertoire de sortie (défaut : répertoire courant)")
        parser.add_argument("--tous-les-tarifs", action="store_true", help="Inclure aussi les tarifs terminés avant la période analysée")
        parser.add_argument("--noms-responsables", action="store_true", help="Inclure les noms des responsables (anonymisés par défaut)")

    def handle(self, *args, **options):
        if options["liste"]:
            for activite in Activite.objects.order_by("-date_debut", "nom"):
                self.stdout.write("%5d  %s  (%s → %s)" % (activite.pk, activite.nom, activite.date_debut or "?", activite.date_fin or "illimitée"))
            return

        if options["toutes"]:
            activites = list(Activite.objects.order_by("pk"))
        elif options["idactivites"]:
            activites = list(Activite.objects.filter(pk__in=options["idactivites"]).order_by("pk"))
            manquantes = set(options["idactivites"]) - {a.pk for a in activites}
            if manquantes:
                raise CommandError("Activité(s) introuvable(s) : %s" % ", ".join(str(i) for i in sorted(manquantes)))
        else:
            raise CommandError("Indiquez un ou plusieurs ID d'activités, --toutes ou --liste")

        os.makedirs(options["sortie"], exist_ok=True)
        for activite in activites:
            try:
                contenu = utils_export_parametrage.Get_json(activite, depuis=options["depuis"], jusqua=options["jusqua"],
                                                            tous_les_tarifs=options["tous_les_tarifs"], noms_responsables=options["noms_responsables"])
            except ValueError as erreur:
                raise CommandError("%s : %s" % (activite.nom, erreur))
            nom_fichier = os.path.join(options["sortie"], utils_export_parametrage.Get_nom_fichier(activite))
            with open(nom_fichier, "w", encoding="utf-8") as fichier:
                fichier.write(contenu)
            self.stdout.write(self.style.SUCCESS("%s → %s (%d Ko)" % (activite.nom, nom_fichier, os.path.getsize(nom_fichier) // 1024 + 1)))
