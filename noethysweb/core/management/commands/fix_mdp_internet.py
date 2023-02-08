# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.management.base import BaseCommand
from core.models import Famille, Utilisateur


class Command(BaseCommand):
    help = 'Correction des mdp internet'

    def handle(self, *args, **kwargs):
        """ Associe de nouveau les codes familles avec la table utilisateur """
        for famille in Famille.objects.select_related("utilisateur"):

            if not famille.utilisateur:

                # Création de l'utilisateur s'il n'existe pas déjà
                utilisateur = Utilisateur(username=famille.internet_identifiant, categorie="famille", force_reset_password=True)
                utilisateur.save()
                utilisateur.set_password(famille.internet_mdp)
                utilisateur.save()
                famille.utilisateur = utilisateur
                famille.save()
                famille.utilisateur.save()

            else:

                # Correction de l'identifiant
                if famille.utilisateur.username != famille.internet_identifiant:
                    famille.utilisateur.username = famille.internet_identifiant

                # Correction du mot de passe
                if not famille.internet_mdp.startswith("custom"):
                    famille.utilisateur.set_password(famille.internet_mdp)
                    famille.utilisateur.force_reset_password = True

                famille.utilisateur.save()

        self.stdout.write(self.style.SUCCESS("Correction des mdp internet OK"))
