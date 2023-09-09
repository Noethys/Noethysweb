#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.apps import AppConfig

class exemple(AppConfig):
    """ Remplacez ci-dessus exemple par le nom du plugin """
    # Remplacez ci-dessous exemple par le nom du plugin
    name = "plugins.exemple"

    # Renseignez ci-dessous un titre pour le menu principal
    titre = "Mon plugin perso"

    # Renseignez le nom d'une icône Font Awesome [optionnel]
    icone = "puzzle-piece"

    # Créez le menu ci-dessous : Nom de la rubrique puis les items sous forme d'une liste de dictionnaires (url, titre, icone [OPTIONNEL])
    menu = [
        ("Mes listes personnalisées", [
            # Exemple d'une liste des règlements uniquement en espèces
            {"url": "liste_reglements_especes", "titre": "Liste des règlements en espèces"},
            # Exemple d'un raccourci vers le paramétrage des médecins
            {"url": "medecins_liste", "titre": "Liste des médecins"},
        ]),
        ("Ma page d'informations", [
            # Exemple d'une page d'informations diverses
            {"url": "informations_diverses", "titre": "Informations diverses"},
        ]),
    ]
