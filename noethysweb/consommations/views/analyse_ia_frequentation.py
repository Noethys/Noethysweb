# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import time
from django.http import JsonResponse
from django.views.generic import TemplateView
from core.views.base import CustomView
from consommations.forms.analyse_ia_frequentation import Formulaire
from consommations.utils import utils_analyse_ia_frequentation


def Exporter(request):
    """ Générer le fichier d'export """
    # Récupération des options
    time.sleep(1)
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ", ".join(messages_erreurs)}, status=401)

    # Exporter
    export = utils_analyse_ia_frequentation.Exporter(request=request, options=form.cleaned_data)
    resultat = export.Generer()
    if not resultat:
        return JsonResponse({"erreurs": export.Get_erreurs_html()}, status=401)
    return JsonResponse({"resultat": "ok", "nom_fichier": resultat})


class View(CustomView, TemplateView):
    menu_code = "analyse_ia_frequentation"
    template_name = "consommations/analyse_ia_frequentation.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Analyse IA de la fréquentation"
        context["colonnes_export"] = utils_analyse_ia_frequentation.COLONNES_EXPORTS
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)

        context["exemples_questions"] = [
            """Tu dois comptabiliser le nombre de journées et de demi-journées sur la période des vacances
                de février 2026, en prenant en compte uniquement les présences et les absences injustifiées et
                uniquement les individus de 3 à 5 enfants.""",
            """Tu dois comptabiliser le nombre de journées (que tu dois multiplier par 8 heures) et le nombre 
                de demi-journées (que tu dois multiplier par 4 heures) en ne prenant en compte que les présents, et les
                dates de vacances, et en séparant les individus de moins de 6 ans et les 6 ans et plus.""",
            """Je veux que tu comptabilises les heures de présences réelles en distinguant les périodes scolaires et les périodes
                de vacances, mais tu dois appliquer un plafond de 9h pour chaque date et chaque individu.""",
            """Tu dois me donner le nombre de repas prévus chaque jour sur la période scolaire uniquement.""",
            """Tu dois analyser la différence entre les dates des consommation et les dates de saisie.""",
            """Quels sont le nombre d'individus et le nombre de familles présentes ?""",
            """Peux-tu me faire une analyse de la fréquentation en fonction de l'âge ?""",
            """J'aimerais les chiffres totaux de la fréquentation regroupés par mois""",
            """Quels sont les jours de la semaine les plus fréquentés ?""",
            """De combien d'animateurs ai-je besoin pour chacune des dates d'ouverture ?""",
            """Peux-tu analyser les consommations en attente ?""",
            """Peux-tu me donner des statistiques de fréquentation pour chaque période ?""",
            """Quelle est la durée totale des consommations (en ne tenant compte que des consommations ayant l'état présent) ?""",
            """Quels sont les évènements qui ont rencontré le plus de succès ? Tu dois uniquement prendre en compte les consommations
            présentes et en absence justifiée tous les samedis sur l'activité jeunesse.""",
            """J'aimerais obtenir le nombre de journées-enfants (C'est-à-dire qu'une journée est égale à 1 et une demi-journée est égale à 0.5)
                pour chaque semaine de la période scolaire en effectuant un regroupement par catégorie de tarif.""",
        ]
        return context
