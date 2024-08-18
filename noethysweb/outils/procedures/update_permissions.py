#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from outils.views.procedures import BaseProcedure


class Procedure(BaseProcedure):
    """ Utilisation : update_permissions --fiches """

    def Arguments(self, parser=None):
        parser.add_argument("--fiches", action="store_true", dest="fiches", default=False, help="Créer les autorisations Modifier des fiches")

    def Executer(self, variables=None):
        # Update des permissions
        logger.debug("Mise à jour manuelle des permissions...")
        from django.core.management import call_command
        call_command("update_permissions")

        from django.db.models import Q
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission

        # Importation des permissions Modifier des fiches familles et individus
        permissions = Permission.objects.filter((Q(codename__startswith="individu_") | Q(codename__startswith="famille_")) & Q(codename__endswith="_modifier"))

        # Attribution des permissions aux utilisateurs
        if variables.fiches:
            logger.debug("Attribution des permissions Modifier sur les fiches...")
            for utilisateur in get_user_model().objects.filter(categorie="utilisateur"):
                for permission in permissions:
                    if not utilisateur.has_perm("core.%s" % permission.codename):
                        utilisateur.user_permissions.add(permission)

        return "Mise à jour des permissions effectuée."
