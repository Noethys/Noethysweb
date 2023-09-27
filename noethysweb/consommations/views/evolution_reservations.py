# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.views.generic import TemplateView
from django.db.models import Q, Count
from core.views.base import CustomView
from core.models import Activite, Historique
from core.utils import utils_dates
from consommations.forms.evolution_reservations import Formulaire


class View(CustomView, TemplateView):
    menu_code = "evolution_reservations"
    template_name = "consommations/evolution_reservations.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Evolution des réservations"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "data": self.Get_data(parametres=form.cleaned_data)
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_data(self, parametres={}):
        data = {"dates": [], "total": [], "ajouts": [], "suppressions": [], "nbre_ajouts": 0, "nbre_suppressions": 0}

        if parametres:

            # Activités
            param_activites = json.loads(parametres["activites"])
            if param_activites["type"] == "groupes_activites":
                liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
            if param_activites["type"] == "activites":
                liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

            # Période
            presents = (utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0]),
                        utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1]))

            # Création des données
            condition = (Q(titre="Ajout d'une consommation") | Q(titre="Suppression d'une consommation")) & Q(activite__in=liste_activites, date__range=presents)
            dict_temp = {}
            donnees = {"total": {}, "ajouts": {}, "suppressions": {}}
            for titre, date, nbre in Historique.objects.filter(condition).values_list("titre", "horodatage__date").annotate(nbre=Count("individu_id", distinct=True)).order_by("horodatage__date"):
                date = str(date)
                dict_temp[date] = dict_temp.get(date, 0) + (-nbre if "Suppression" in titre else nbre)
                if "Ajout" in titre: donnees["ajouts"][date] = nbre
                if "Suppression" in titre: donnees["suppressions"][date] = -nbre
                if date not in data["dates"]: data["dates"].append(date)

            # Courbe de l'évolution
            x = 0
            for date, nbre in dict_temp.items():
                x += nbre
                donnees["total"][date] = x


            for date in data["dates"]:
                for categorie in ("total", "ajouts", "suppressions"):
                    data[categorie].append(donnees[categorie].get(date, None))

            # Totaux pour légende
            data["nbre_ajouts"] = sum(filter(None, data["ajouts"]))
            data["nbre_suppressions"] = -sum(filter(None, data["suppressions"])) or 0

        return json.dumps(data)
