# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import d'un fichier Domino dans la base"

    def add_arguments(self, parser):
        parser.add_argument("fichier", type=str, help="Nom du fichier")

    def handle(self, *args, **kwargs):
        nom_fichier = kwargs["fichier"]

        from outils.utils import utils_import_domino
        utils_import_domino.Import(nom_fichier)
