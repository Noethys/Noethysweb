# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Utilisateur


class Command(BaseCommand):
    help = 'Correction des mdp internet'

    def handle(self, *args, **kwargs):
        """ Associe de nouveau les codes familles avec la table utilisateur """
        for utilisateur in Utilisateur.objects.select_related("famille").filter(categorie="famille"):

            # Correction de l'identifiant
            if utilisateur.username != utilisateur.famille.internet_identifiant:
                utilisateur.username = utilisateur.famille.internet_identifiant

            # Correction du mot de passe
            if not utilisateur.famille.internet_mdp.startswith("custom"):
                utilisateur.set_password(utilisateur.famille.internet_mdp)
                utilisateur.force_reset_password = True

            utilisateur.save()

        self.stdout.write(self.style.SUCCESS("Correction des mdp internet OK"))
