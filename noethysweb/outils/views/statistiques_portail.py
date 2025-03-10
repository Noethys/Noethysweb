# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, calendar
from django.db.models import Q, Count
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.models import Famille, Rattachement, Vacance, Historique, Consentement, JOURS_COMPLETS_SEMAINE
from core.utils import utils_dates
from outils.forms.statistiques_portail import Formulaire
from outils.views.statistiques import Texte, Tableau, Camembert, Histogramme, Titre, Espace


class View(CustomView, TemplateView):
    menu_code = "statistiques_portail"
    template_name = "outils/statistiques.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Statistiques du portail"
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
        data = []

        if parametres:
            for rubrique in parametres["rubriques"]:

                # Période sélectionnée
                if parametres["type_periode"] == "ANNEE":
                    dates = (datetime.date(parametres["annee"], 1, 1), datetime.date(parametres["annee"], 12, 31))
                elif parametres["type_periode"] == "MOIS":
                    dates = (datetime.date(parametres["annee"], int(parametres["mois"]), 1), datetime.date(parametres["annee"], int(parametres["mois"]), calendar.monthrange(parametres["annee"], int(parametres["mois"]))[1]))
                elif parametres["type_periode"] == "VACANCES":
                    vacance = Vacance.objects.get(nom=parametres["vacances"], annee=parametres["annee"])
                    dates = (vacance.date_debut, vacance.date_fin)
                elif parametres["type_periode"] == "PERIODE":
                    dates = (utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0]), utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1]))
                else:
                    return []

                # ---------------------------- Connexions -------------------------------
                if rubrique == "connexions":
                    data.append(Titre(texte="Connexions"))

                    condition = Q(titre="Connexion au portail", horodatage__range=dates)

                    # Texte : Nombre total de connexions
                    data.append(Texte(texte="%d connexions sur la période." % Historique.objects.filter(condition).distinct().count(),))

                    # Chart : Nombre de connexions par date
                    donnees = Historique.objects.filter(condition).values_list("horodatage__date").annotate(nbre=Count("idaction", distinct=True)).order_by("horodatage__date")
                    data.append(Histogramme(
                        titre="Nombre de connexions par date", type_chart="bar", chronologie="date",
                        labels=[str(date) for date, nbre in donnees],
                        valeurs=[nbre for date, nbre in donnees],
                    ))

                    # Chart : Nombre de connexions par heure
                    donnees = {heure: 0 for heure in range(0, 24)}
                    donnees.update({heure: nbre for heure, nbre in Historique.objects.filter(condition).values_list("horodatage__hour").annotate(nbre=Count("idaction", distinct=True))})
                    resultats = [(heure, nbre) for heure, nbre in donnees.items()]
                    resultats.sort()
                    data.append(Histogramme(titre="Nombre de connexions par heure", type_chart="bar",
                        labels=["%dh" % heure for heure, nbre in resultats],
                        valeurs=[nbre for heure, nbre in resultats],
                    ))

                    # Chart : Nombre de connexions par jour de la semaine
                    donnees = {index+1: 0 for index, label_jour in JOURS_COMPLETS_SEMAINE}
                    donnees.update({jour: nbre for jour, nbre in Historique.objects.filter(condition).values_list("horodatage__iso_week_day").annotate(nbre=Count("idaction", distinct=True))})
                    resultats = [(jour, nbre) for jour, nbre in donnees.items()]
                    resultats.sort()
                    data.append(Histogramme(titre="Nombre de connexions par jour de la semaine", type_chart="bar",
                        labels=[label_jour for index, label_jour in JOURS_COMPLETS_SEMAINE],
                        valeurs=[nbre for jour, nbre in resultats],
                    ))

                # ---------------------------- Renseignements -------------------------------
                if rubrique == "renseignements":
                    data.append(Titre(texte="Renseignements"))

                    condition = Q(portail=True, horodatage__range=dates)
                    donnees = Historique.objects.filter(condition).values_list("titre").annotate(nbre=Count("idaction", distinct=True)).order_by("titre")
                    resultats = {}
                    for titre, nbre in donnees:
                        for code, label in [("identité", "Identité"), ("caisse", "Caisse"), ("médecin", "Médecin"), ("coordonnées", "Coordonnées"), ("maladie", "Maladies"), ("régimes", "Régimes alimentaires"), ("contact", "Contacts"), ("assurance", "Assurances"), ("information", "Informations personnelles"), ("vaccination", "Vaccinations")]:
                            if code in titre:
                                resultats.setdefault(label, 0)
                                resultats[label] += nbre

                    # Texte : Nombre total de renseignements modifiés
                    data.append(Texte(texte="%d renseignements modifiés sur la période." % sum(resultats.values()),))

                    # Camembert : Catégories de renseignements modifiés
                    donnees = [(label, nbre) for label, nbre in resultats.items()]
                    data.append(Camembert(
                        titre="Catégories de renseignements modifiés",
                        labels=[item[0] for item in donnees],
                        valeurs=[item[1] for item in donnees],
                    ))

                    # Tableau : Certification des fiches
                    nbre_familles = Famille.objects.filter(certification_date__range=dates).distinct().count()
                    nbre_individus = Rattachement.objects.filter(certification_date__range=dates).distinct().count()
                    data.append(Tableau(
                        titre="Certification des fiches",
                        colonnes=["Type de fiche", "Nombre de certifications"],
                        lignes=[("Fiche famille", nbre_familles), ("Fiche individuelle", nbre_individus)]
                    ))

                    # Tableau : Consentements
                    donnees = Consentement.objects.filter(horodatage__range=dates).values_list("unite_consentement__type_consentement__nom").annotate(nbre=Count("idconsentement", distinct=True)).order_by("unite_consentement__type_consentement__nom")
                    if donnees:
                        data.append(Tableau(
                            titre="Consentements",
                            colonnes=["Type de consentement", "Nombre"],
                            lignes=donnees,
                        ))

                # ---------------------------- Réservations -------------------------------
                if rubrique == "reservations":
                    data.append(Titre(texte="Réservations"))

                    # Chart : Nombre d'ajouts et de suppressions de consommations
                    for type_action in ("Ajout", "Suppression"):
                        condition = Q(titre="%s d'une consommation" % type_action, horodatage__range=dates, utilisateur__famille__isnull=False)
                        donnees = Historique.objects.filter(condition).values_list("horodatage__date").annotate(nbre=Count("idaction", distinct=True)).order_by("horodatage__date")
                        data.append(Histogramme(
                            titre="Nombre %ss de consommations par date" % type_action.lower(), type_chart="bar", chronologie="date",
                            labels=[str(date) for date, nbre in donnees],
                            valeurs=[nbre for date, nbre in donnees],
                        ))

                data.append(Espace(hauteur=50))

        return data
