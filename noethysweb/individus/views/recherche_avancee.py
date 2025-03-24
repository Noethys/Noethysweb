# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime
logger = logging.getLogger(__name__)
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib import messages
from core.views.base import CustomView
from core.models import Rattachement
from individus.forms.recherche_avancee import Formulaire


class View(CustomView, TemplateView):
    menu_code = "individus_recherche_avancee"
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Recherche avancée d'individus"
        context['box_titre'] = "Effectuer une recherche avancée d'individus"
        context['box_introduction'] = "Saisissez un ou plusieurs critères de recherche et cliquez sur le bouton Rechercher. Si la recherche textuelle ne suffit pas, essayez la recherche phonétique."
        context['form'] = context.get("form", Formulaire)
        return context

    def post(self, request, **kwargs):
        # Validation du form
        form = Formulaire(request.POST, request.FILES, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Champs de recherche
        champs_recherche = form.changed_data
        if "type_recherche" in champs_recherche:
            champs_recherche.remove("type_recherche")
        if not champs_recherche:
            messages.add_message(request, messages.ERROR, "Vous devez renseigner au moins un critère de recherche")
            return self.render_to_response(self.get_context_data(form=form))

        # Recherche des résultats
        import jellyfish

        resultats = {}
        rattachements = Rattachement.objects.select_related("individu", "famille").all()
        for rattachement in rattachements:
            score = resultats.get(rattachement, 0)

            for nom_champ in champs_recherche:
                valeur_recherche = form.cleaned_data[nom_champ]
                valeur_individu = getattr(rattachement.individu, nom_champ, "")

                # Recherche de texte
                if isinstance(valeur_individu, str):
                    # Recherche textuelle
                    if form.cleaned_data["type_recherche"] == "PHONETIQUE":
                        if jellyfish.soundex(valeur_recherche) == jellyfish.soundex(valeur_individu):
                            if valeur_recherche.startswith("H"): valeur_recherche = valeur_recherche[1:]
                            if valeur_individu.startswith("H"): valeur_individu = valeur_individu[1:]
                            try:
                                distance = jellyfish.jaro_distance(valeur_recherche.lower(), valeur_individu.lower())
                            except:
                                distance = jellyfish.jaro_similarity(valeur_recherche.lower(), valeur_individu.lower())
                            score += 1 + distance

                    # Recherche phonétique
                    if form.cleaned_data["type_recherche"] == "TEXTE":
                        try:
                            distance = jellyfish.jaro_distance(valeur_recherche.lower(), valeur_individu.lower())
                        except:
                            distance = jellyfish.jaro_similarity(valeur_recherche.lower(), valeur_individu.lower())
                        score += distance

                    if score >= 0.75:
                        resultats[rattachement] = score

                # Recherche de date
                if isinstance(valeur_individu, datetime.date):
                    if valeur_recherche == valeur_individu:
                        resultats[rattachement] = score

        # Tri par score
        resultats = sorted([(score, rattachement) for rattachement, score in resultats.items()], key=lambda donnees: donnees[0], reverse=True)

        # Envoi des 50 premiers résultats
        context = self.get_context_data(**kwargs)
        context["rattachements"] = [r[1] for r in resultats[:50]]
        return render(request, "individus/recherche_avancee.html", context)
