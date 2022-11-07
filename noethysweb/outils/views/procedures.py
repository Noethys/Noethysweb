# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import argparse, importlib
from django.views.generic import TemplateView
from core.views.base import CustomView
from outils.forms.procedures import Formulaire


class BaseProcedure:
    def Arguments(self, parser=None):
        pass

    def Executer(self):
        pass


class View(CustomView, TemplateView):
    menu_code = "procedures"
    template_name = "outils/procedures.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Procédures"
        if "form" not in kwargs:
            context["form"] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form": form,
            "resultat": self.Executer(commande=form.cleaned_data["commande"])
        }
        return self.render_to_response(self.get_context_data(**context))

    def Executer(self, commande=""):
        # Analyse de la commande
        if " " in commande:
            texte_fonction = commande.split(" ")[0].strip()
            texte_arguments = commande.replace(texte_fonction, "").strip()
        else:
            texte_fonction = commande.strip()
            texte_arguments = ""

        try:
            # Ouverture du module
            module = importlib.import_module("outils.procedures.%s" % texte_fonction)
            procedure = module.Procedure()
        except Exception as err:
            return "Le module %s n'a pas été trouvé dans le répertoire des procédures." % texte_fonction

        try:
            parser = argparse.ArgumentParser()
            procedure.Arguments(parser=parser)
            if texte_arguments:
                liste_arguments = texte_arguments.split(" ") if " " in texte_arguments else [texte_arguments]
            else:
                liste_arguments = []
            variables = parser.parse_args(liste_arguments)
        except SystemExit:
            return "Une erreur a été détectée dans les arguments de la commande."

        try:
            # Exécution de la procédure
            resultat = procedure.Executer(variables=variables)
            return resultat
        except Exception as err:
            return err
