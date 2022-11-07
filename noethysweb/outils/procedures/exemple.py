#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging
logger = logging.getLogger(__name__)
from outils.views.procedures import BaseProcedure


class Procedure(BaseProcedure):
    """
    Exemple de procédure personnalisée
    Pour essayer, taper la commande suivante : "exemple Paris" et faire Entrée
    """
    def Arguments(self, parser=None):
        parser.add_argument("nom", type=str)

    def Executer(self, variables=None):
        return "Voici le nom : %s." % variables.nom
