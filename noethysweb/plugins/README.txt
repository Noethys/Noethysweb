==========================================
Créer et intégrer votre plugin Noethysweb
==========================================

--- CREER LE NOUVEAU PLUGIN ---

1. Dupliquez le répertoire exemple qui se trouve dans le répertoire plugins. Vous l'utiliserez comme base pour votre plugin.
2. Donnez à votre nouveau répertoire un nom en minuscules sans espaces. Exemple : monpluginperso.
3. Changez le nom du répertoire templates/exemple en templates/monpluginperso

--- CONNECTER LE PLUGIN A NOETHYSWEB ---

4. Ouvrez le fichier noethysweb\settings_production.py et ajoutez la ligne suivante : PLUGINS = ["monpluginperso"]
Si vous avez plusieurs plugins, ajoutez une liste du type : PLUGINS = ["monpluginperso", "monplugin2", "monplugin3"]

--- PERSONNALISER LES PARAMETRES DU PLUGIN ---

5. Ouvrez le nouveau répertoire de votre plugin.
6. Ouvrez le fichier apps.py et personnalisez-le en fonction des indications.
7. Ouvrez le fichier urls.py et personnalisez-le en fonction des indications.

--- CODER VOTRE PLUGIN ---

8. Vous n'avez plus qu'à créer des forms, views et templates dans les répertoires éponymes. Les urls sont à paramétrer dans le fichier urls.py.

Pour vous aider à coder votre plugin :
- Retrouvez la documentation en français du framework Django sur le site officiel : www.djangoproject.com
- Parcourez les répertoires des modules existants : locations, cotisations, etc... pour vous inspirer des fonctionnalités officielles de Noethysweb.

--- FINALISATION ---

Afin d'ajouter la gestion des droits d'accès à votre plugin, il est nécessaire de générer les permissions. Depuis une console, placez-vous à la racine du répertoire noethysweb et tapez :
python3 manage.py update_permissions
