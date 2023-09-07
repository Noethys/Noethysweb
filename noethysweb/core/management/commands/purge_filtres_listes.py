# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Supprime les filtres de liste d'un utilisateur"

    def add_arguments(self, parser):
        parser.add_argument("idutilisateur", type=int, help="ID de l'utilisateur")

    def handle(self, *args, **kwargs):
        from core.models import FiltreListe
        FiltreListe.objects.filter(utilisateur_id=kwargs["idutilisateur"]).delete()
        self.stdout.write(self.style.SUCCESS("Purge des filtres de listes OK"))
