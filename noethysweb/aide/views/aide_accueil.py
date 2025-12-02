# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import importlib
from django.views.generic import TemplateView
from core.views.base import CustomView
from aide.utils.utils_ressources import Get_ressources


class View(CustomView, TemplateView):
    template_name = "aide/aide_accueil.html"
    menu_code = "aide_accueil"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Aide"
        context["ressources"] = Get_ressources()

        # Recherche une liste de ressources personnalisée dans le répertoire site-packages de python
        # Pour créer votre liste personnalisée, dupliquez le fichier "noethysweb/aide/utils/utils_ressources.py" à la racine,
        # du répertoire site-packages, modifiez son contenu, et nommez-le "noethysweb_aide_custom.py"
        try:
            module = importlib.import_module("noethysweb_aide_custom")
            context["ressources"] = module.Get_ressources()
        except:
            pass

        # Recherche une liste de ressources personnalisée dans le répertoire d'installation de Noethysweb
        # Pour créer votre liste personnalisée, dupliquez le fichier "utils_ressources.py" dans le répertoire "noethysweb/aide/utils",
        # modifiez son contenu, et nommez-le "utils_ressources_custom.py"
        try:
            module = importlib.import_module("aide.utils.utils_ressources_custom")
            context["ressources"] = module.Get_ressources()
        except:
            pass

        return context
