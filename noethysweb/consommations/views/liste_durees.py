# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.views.generic import TemplateView
from django.db.models import Count, F, CharField, Value
from django.db.models.functions import Concat
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Consommation
from consommations.forms.liste_durees import Formulaire


class View(CustomView, TemplateView):
    menu_code = "liste_durees"
    template_name = "consommations/liste_durees.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Liste des durées"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))

        liste_colonnes, liste_lignes = self.Get_resultats(parametres=form.cleaned_data)
        context = {
            "form_parametres": form,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        date_debut = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0])
        date_fin = utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1])

        # Colonnes
        liste_colonnes = ["Date", "Unité", "Evénement", "Début", "Fin", "Durée", "Nbre conso", "Total"]

        # Lignes
        qs = Consommation.objects.select_related("evenement", "unite") \
            .filter(activite=parametres["activite"], date__gte=date_debut, date__lte=date_fin, etat__in=parametres["etats"]) \
            .order_by("date") \
            .annotate(doublon_id=Concat(F("date"), Value("_"), F("heure_debut"), Value("_"), F("heure_fin"), Value("_"), F("unite"), F("evenement"), output_field=CharField()))
        resultats = qs.values("date", "heure_debut", "heure_fin", "unite__nom", "evenement__nom", "evenement__equiv_heures").annotate(nbre_doublons=Count("doublon_id"))

        liste_lignes = []
        for r in resultats:
            if r["evenement__equiv_heures"] and parametres["utiliser_equiv_heures"]:
                duree = utils_dates.TimeEnDelta(r["evenement__equiv_heures"])
            elif r["heure_debut"] and r["heure_fin"]:
                duree = utils_dates.TimeEnDelta(r["heure_fin"]) - utils_dates.TimeEnDelta(r["heure_debut"])
            else:
                duree = datetime.timedelta(minutes=0)
            liste_lignes.append((
                utils_dates.ConvertDateToFR(r["date"]),
                r["unite__nom"],
                r["evenement__nom"] or "",
                r["heure_debut"].strftime("%H:%M") if r["heure_debut"] else "",
                r["heure_fin"].strftime("%H:%M") if r["heure_fin"] else "",
                utils_dates.DeltaEnStr(duree, separateur=":") if duree else "",
                r["nbre_doublons"],
                utils_dates.DeltaEnStr(duree * r["nbre_doublons"], separateur=":") if duree else "",
            ))

        return liste_colonnes, liste_lignes
