Noethysweb
==================
Noethysweb est la version fullweb de Noethys, le logiciel de gestion libre et gratuit de gestion multi-activités pour 
les accueils de loisirs, crèches, garderies périscolaires, cantines, TAP ou NAP, clubs sportifs et culturels...

Plus d'infos sur www.noethys.com

###### Actuellement en test : Soyez vigilants lors d'une utilisation en production.

Installation
------------------------

- Téléchargez le code source.
- Installez python 3.
- Si vous êtes en prod, installez les dépendances du fichier *requirements.txt* :
    - `pip3 install -r requirements.txt`
- Si vous êtes en dev, installez les dépendances du fichier *requirements-dev.txt* :
    - `pip3 install -r requirements-dev.txt`
- Allez dans le répertoire *noethysweb/noethysweb* et renommez le fichier *settings_production_modele.py* en *settings_production.py*.
- Personnalisez le fichier *settings_production.py* selon vos besoins.
- Exécutez les commandes suivantes depuis le répertoire *noethysweb* :
    - `python3 manage.py makemigrations`
    - `python3 manage.py migrate`
    - `python3 manage.py collectstatic`
    - `python3 manage.py createsuperuser`
    - `python3 manage.py update_permissions`
- Si vous souhaitez commencer avec une base de données vide :
    - `python3 manage.py import_defaut`
- Ou si vous souhaitez importer la base de données d'un fichier Noethys - où xxx est le nom du fichier d'export créé depuis la fonction "Exporter vers Noethysweb" du menu Fichier de Noethys, et motdepasse est le mot de passe saisi lors de la génération de l'export :
    - `python3 manage.py import_fichier xxx.nweb motdepasse`
- Lancez enfin le serveur intégré (Uniquement pour des tests) :
    - `python3 manage.py runserver`
- Consultez le site www.djangoproject.com pour en savoir davantage sur les options et le déploiement.

Utilisation
------------------------

1. Allez sur le portail utilisateur (par défaut : http://127.0.0.1:8000/utilisateur/) pour paramétrer l'organisateur, les structures, les activités, les jours fériés, les périodes de vacances, etc... puis créez les familles et les individus.
2. Allez sur le portail administrateur (par défaut : http://127.0.0.1:8000/administrateur/) pour créer de nouveaux utilisateurs et leur attribuer les droits d'accès et les associer aux structures.
3. Communiquez l'url du portail aux familles (par défaut : http://127.0.0.1:8000/).
