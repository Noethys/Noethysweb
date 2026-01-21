# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import d'un fichier CERIG dans la base. Le fichiers XLSX doit se trouver à la racine."

    def add_arguments(self, parser):
        parser.add_argument("nom_fichier", type=str, help="Nom du fichier xlsx")

    def handle(self, *args, **kwargs):
        from outils.utils import utils_import_cerig
        utils_import_cerig.Importer(nom_fichier=kwargs["nom_fichier"])
