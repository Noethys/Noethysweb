#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'noethysweb.settings')

application = get_wsgi_application()

try:
    from django.core.management import call_command
    call_command("crontab", "add")
except Exception as err:
    print("Impossible d'initialiser le crontab :", err)

# Date de la dernière update pour l'auto reload wsgi
# lastupdate = 2020-01-01 15:29:53.324395