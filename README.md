Noethysweb
==================
Noethysweb est la version fullweb de Noethys, le logiciel de gestion libre et gratuit de gestion multi-activités pour 
les accueils de loisirs, crèches, garderies périscolaires, cantines, TAP ou NAP, clubs sportifs et culturels...

Plus d'infos sur www.noethys.com


Installation
------------------------

- Téléchargez le code source.
- Installez python 3 et les dépendances (Voir requirements.txt).
- Allez dans le répertoire *noethysweb/noethysweb* et renommez le fichier *settings_production_modele.py* en *settings_production.py*.
- Personnalisez le fichier *settings_production.py* selon vos besoins.
- Exécutez les commandes suivantes depuis le répertoire *noethysweb* :
    - `python3 manage.py migrate`
    - `python3 manage.py collectstatic`
    - `python3 manage.py createsuperuser`
    - `python3 manage.py update_permissions`
    - `python3 manage.py runserver`
- Consultez le site www.djangoproject.com pour en savoir davantage sur les options et le déploiement.
