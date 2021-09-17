Noethysweb
==================
Noethysweb est la version fullweb de Noethys, le logiciel de gestion libre et gratuit de gestion multi-activités pour 
les accueils de loisirs, crèches, garderies périscolaires, cantines, TAP ou NAP, clubs sportifs et culturels...

Plus d'infos sur www.noethys.com

###### Développement en cours : Ne pas utiliser en production.

Installation
------------------------

- Téléchargez le code source.
- Installez python 3 et les dépendances (Voir requirements.txt).
- Allez dans le répertoire *noethysweb/noethysweb* et renommez le fichier *settings_production_modele.py* en *settings_production.py*.
- Personnalisez le fichier *settings_production.py* selon vos besoins.
- Exécutez les commandes suivantes depuis le répertoire *noethysweb* :
    - `python3 manage.py makemigrations`
    - `python3 manage.py migrate`
    - `python3 manage.py collectstatic`
    - `python3 manage.py createsuperuser`
    - `python3 manage.py update_permissions`
    - `python3 manage.py import_defaut` (Uniquement si vous souhaitez importer les données par défaut : jours fériés, modèles, documents...)
    - `python3 manage.py runserver`
- Consultez le site www.djangoproject.com pour en savoir davantage sur les options et le déploiement.

Utilisation
------------------------

1. Allez sur le portail utilisateur (par défaut : http://127.0.0.1:8000/utilisateur/) pour paramétrer l'organisateur, les structures, les activités, les jours fériés, les périodes de vacances, etc... puis créez les familles et les individus.
2. Allez sur le portail administrateur (par défaut : http://127.0.0.1:8000/administrateur/) pour créer de nouveaux utilisateurs et leur attribuer les droits d'accès et les associer aux structures.
3. Communiquez l'url du portail aux familles (par défaut : http://127.0.0.1:8000/).
