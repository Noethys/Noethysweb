Noethysweb
==================
Noethysweb est la version fullweb de Noethys, le logiciel de gestion libre et gratuit de gestion multi-activités pour 
les accueils de loisirs, crèches, garderies périscolaires, cantines, TAP ou NAP, clubs sportifs et culturels...

Plus d'infos sur www.noethys.com

###### Actuellement en test : Soyez vigilants lors d'une utilisation en production.

Installation
------------------------

- Téléchargez le code source.
- Installez python 3.9
- Allez dans le répertoire d'installation
    - `python3.9 -m venv venv`
- Installez les dépendances du fichier *requirements.txt*
    - `./venv/bin/python install -r requirements.txt`
- Allez dans le répertoire *noethysweb/noethysweb* et renommez le fichier *settings_production_modele.py* en *settings_production.py*.
- Personnalisez le fichier *settings_production.py* selon vos besoins.
- Exécutez les commandes suivantes depuis le répertoire *noethysweb* :
    - `../venv/bin/python manage.py makemigrations`
    - `../venv/bin/python manage.py migrate`
    - `../venv/bin/python manage.py collectstatic`
    - `../venv/bin/python manage.py createsuperuser`
    - `../venv/bin/python manage.py update_permissions`
- Si vous souhaitez commencer avec une base de données vide :
    - `../venv/bin/python manage.py import_defaut`
- Ou si vous souhaitez importer la base de données d'un fichier Noethys - où xxx est le nom du fichier d'export créé depuis la fonction "Exporter vers Noethysweb" du menu Fichier de Noethys, et motdepasse est le mot de passe saisi lors de la génération de l'export :
    - `../venv/bin/python manage.py import_fichier xxx.nweb motdepasse`
- Lancez enfin le serveur intégré (Uniquement pour des tests) :
    - `../venv/bin/python manage.py runserver`
- Consultez le site www.djangoproject.com pour en savoir davantage sur les options et le déploiement.  
  Exemple utilisant [Gunicorn](https://gunicorn.org/):
  - Service systemd */etc/systemd/system/noethysweb.service*
    ```ini
    [Unit]
    Description=noethysweb
    After=network.target

    [Service]
    Type=notify
    User=apache
    Group=apache
    # Chemin du dossier dans lequel est manage.py
    WorkingDirectory=/chemin/vers/Noethysweb/noethysweb
    ExecStart=/chemin/vers/Noethysweb/venv/bin/gunicorn
    ExecReload=/bin/kill -s HUP $MAINPID
    KillMode=mixed
    TimeoutStopSec=5

    [Install]
    WantedBy=multi-user.target
    ```
  - Activez dans *settings_production.py* la variable `GUNICORN_PIDFILE` pour que le reload du code se fasse lors des mises à jour
  - Vous pouvez ensuite utiliser la configuration suivante pour Apache:
    ```apacheconf
    # Fichiers statiques
    ProxyPass "/static/" "!"
    ProxyPass "/media/" "!"
    RewriteEngine On
    RewriteRule ^/(?:static|media)/.+$ /noethysweb$0 [L]

    # Le reste est transmis à Gunicorn
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto https
    ProxyPass "/" unix:/chemin/vers/Noethysweb/gunicorn.sock|http://localhost/
    ```

Utilisation
------------------------

1. Allez sur le portail utilisateur (par défaut : http://127.0.0.1:8000/utilisateur/) pour paramétrer l'organisateur, les structures, les activités, les jours fériés, les périodes de vacances, etc... puis créez les familles et les individus.
2. Allez sur le portail administrateur (par défaut : http://127.0.0.1:8000/administrateur/) pour créer de nouveaux utilisateurs et leur attribuer les droits d'accès et les associer aux structures.
3. Communiquez l'url du portail aux familles (par défaut : http://127.0.0.1:8000/).
