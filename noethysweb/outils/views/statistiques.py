# -*- coding: utf-8 -*-

#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.base import CustomView
from django.db.models import Q, Count
from core.models import Activite, Consommation, Inscription, Famille, Individu, Vacance, Scolarite, LISTE_MOIS
from django.views.generic import TemplateView
from outils.forms.statistiques import Formulaire
from core.utils import utils_dates
import json, random, datetime, calendar, operator
from django.db.models import Max, Min


class Element():
    def __init__(self, *args, **kwargs):
        self.id = random.randint(1, 100000)
        self.categorie = ""


class Texte(Element):
    def __init__(self, texte=""):
        Element.__init__(self)
        self.categorie = "texte"
        self.texte = texte


class Tableau(Element):
    def __init__(self, titre="", colonnes=[], lignes=[]):
        Element.__init__(self)
        self.categorie = "tableau"
        self.titre = titre
        self.colonnes = colonnes
        self.lignes = lignes


class Camembert(Element):
    def __init__(self, titre="", labels=[], valeurs=[], couleurs=[]):
        Element.__init__(self)
        self.categorie = "camembert"
        self.titre = titre
        self.labels = labels
        self.valeurs = valeurs
        if couleurs:
            self.couleurs = couleurs
        else:
            self.couleurs = []
            for valeur in self.valeurs:
                self.couleurs.append("rgba(%d, %d, %d, 0.5)"% (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))


class Histogramme(Element):
    def __init__(self, titre="", labels=[], type_chart="line", valeurs=[]):
        Element.__init__(self)
        self.categorie = "histogramme"
        self.type_chart = type_chart # "line" ou "bar"
        self.titre = titre
        self.labels = labels
        self.valeurs = valeurs


def Calcule_periodes_comparatives(parametres={}, presents=None, liste_activites=[]):
    dates_extremes = Consommation.objects.filter(activite__in=liste_activites, etat__in=("reservation", "present")).aggregate(Min('date'), Max('date'))
    if dates_extremes["date__min"] and dates_extremes["date__max"]:
        liste_periodes = []

        if parametres["donnees"] == "VACANCES":
            for vacance in Vacance.objects.filter(nom=parametres["vacances"], date_debut__gte=dates_extremes["date__min"], date_fin__lte=dates_extremes["date__max"]).order_by("date_debut"):
                liste_periodes.append({"date_debut": vacance.date_debut, "date_fin": vacance.date_fin, "label": "%s %d" % (parametres["vacances"], vacance.annee)})

        if parametres["donnees"] == "MOIS":
            for annee in range(dates_extremes["date__min"].year, dates_extremes["date__max"].year + 1):
                liste_periodes.append(
                    {"date_debut": datetime.date(annee, int(parametres["mois"]), 1),
                     "date_fin": datetime.date(annee, int(parametres["mois"]), calendar.monthrange(annee, int(parametres["mois"]))[1]),
                     "label": "%s %d" % (LISTE_MOIS[int(parametres["mois"]) - 1][1], annee)})

        if parametres["donnees"] == "ANNEE":
            for annee in range(dates_extremes["date__min"].year, dates_extremes["date__max"].year + 1):
                liste_periodes.append({"date_debut": datetime.date(annee, 1, 1), "date_fin": datetime.date(annee, 12, 31), "label": "Année %d" % annee})

        if parametres["donnees"] == "PERIODE":
            if presents[0].year == presents[1].year:
                for annee in range(dates_extremes["date__min"].year, dates_extremes["date__max"].year + 1):
                    nbreJoursMois = calendar.monthrange(annee, presents[0].month)[1]
                    if presents[0].day < nbreJoursMois:
                        date_debut_temp = datetime.date(annee, presents[0].month, presents[0].day)
                    else:
                        date_debut_temp = datetime.date(annee, presents[0].month, nbreJoursMois)
                    nbreJoursMois = calendar.monthrange(annee, presents[1].month)[1]
                    if presents[1].day < nbreJoursMois:
                        date_fin_temp = datetime.date(annee, presents[1].month, presents[1].day)
                    else:
                        date_fin_temp = datetime.date(annee, presents[1].month, nbreJoursMois)
                    label = "Du %s au %s" % (utils_dates.ConvertDateToFR(date_debut_temp), utils_dates.ConvertDateToFR(date_fin_temp))
                    dictTemp = {"date_debut": date_debut_temp, "date_fin": date_fin_temp, "label": label}
                    liste_periodes.append(dictTemp)
    return liste_periodes




class View(CustomView, TemplateView):
    menu_code = "statistiques"
    template_name = "outils/statistiques.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Statistiques"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire()
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "data": self.Get_data(parametres=form.cleaned_data)
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_data(self, parametres={}):
        data = []

        if parametres:
            # Rubrique
            rubrique = parametres["rubrique"]

            # Activités
            param_activites = json.loads(parametres["activites"])
            if param_activites["type"] == "groupes_activites":
                liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
            if param_activites["type"] == "activites":
                liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

            # Données
            if parametres["donnees"] == "ANNEE":
                presents = (datetime.date(parametres["annee"], 1, 1),
                            datetime.date(parametres["annee"], 12, 31))
            elif parametres["donnees"] == "MOIS":
                presents = (datetime.date(parametres["annee"], int(parametres["mois"]), 1),
                            datetime.date(parametres["annee"], int(parametres["mois"]), calendar.monthrange(parametres["annee"], int(parametres["mois"]))[1]))
            elif parametres["donnees"] == "VACANCES":
                vacance = Vacance.objects.get(nom=parametres["vacances"], annee=parametres["annee"])
                presents = (vacance.date_debut, vacance.date_fin)
            elif parametres["donnees"] == "PERIODE":
                presents = (utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[0]),
                            utils_dates.ConvertDateENGtoDate(parametres["periode"].split(";")[1]))
            else:
                presents = None


            # ================================ INDIVIDUS ====================================

            if rubrique.startswith("individus"):
                if presents:
                    condition = Q(consommation__activite__in=liste_activites, consommation__date__gte=presents[0], consommation__date__lte=presents[1], consommation__etat__in=("present", "reservation"))
                else:
                    condition = Q(inscription__activite__in=liste_activites)


            # ---------------------------- INDIVIDUS : Nombre -------------------------------
            if rubrique == "individus_nombre":

                # Texte : Nombre d'individus total
                data.append(Texte(texte="%d individus %s." % (Individu.objects.filter(condition).distinct().count(), "présents" if presents else "inscrits")))

                # Tableau : Répartition des individus par activité
                individus = Individu.objects.filter(condition).values_list("%s__activite__nom" % ("consommation" if presents else "inscription")).annotate(nbre=Count("idindividu", distinct=True)).order_by("-nbre")
                data.append(Tableau(
                    titre="Répartition du nombre d'individus par activité",
                    colonnes=["Activité", "Nombre d'individus"],
                    lignes=[(item[0], item[1]) for item in individus]
                ))

                # Chart : Evolution du nombre d'individus - comparatif par période
                if presents:
                    liste_periodes= Calcule_periodes_comparatives(parametres, presents, liste_activites)
                    if liste_periodes:
                        liste_labels, liste_valeurs = [], []
                        for dict_periode in liste_periodes:
                            condition_temp = Q(consommation__activite__in=liste_activites, consommation__date__gte=dict_periode["date_debut"], consommation__date__lte=dict_periode["date_fin"], consommation__etat__in=("present", "reservation"))
                            liste_labels.append(dict_periode["label"])
                            liste_valeurs.append(Individu.objects.filter(condition_temp).distinct().count())
                        data.append(Histogramme(titre="Evolution du nombre des individus", type_chart="bar", labels=liste_labels, valeurs=liste_valeurs))

                # Chart : Nombre d'individus par date
                if presents:
                    individus = Individu.objects.filter(condition).values_list('consommation__date').annotate(nbre=Count('idindividu', distinct=True)).order_by('consommation__date')
                    data.append(Histogramme(
                        titre="Nombre individus par date", type_chart="line",
                        labels=[utils_dates.ConvertDateToFR(date) for date, nbre in individus],
                        valeurs=[nbre for date, nbre in individus],
                    ))



            # ---------------------------- INDIVIDUS : Genre -------------------------------
            if rubrique == "individus_genre":

                individus = Individu.objects.filter(condition).values_list("civilite").annotate(nbre=Count("idindividu", distinct=True))
                resultats = {"M": 0, "F": 0}
                for item in individus:
                    if item[0] in (1, 4): resultats["M"] += item[1]
                    if item[0] in (2, 3, 5): resultats["F"] += item[1]

                # Tableau : Répartition par genre
                data.append(Tableau(
                    titre="Répartition par genre",
                    colonnes=["Genre", "Nombre d'individus"],
                    lignes=[("Garçons", resultats["M"]), ("Filles", resultats["F"])]
                ))

                # Camembert : Répartition par genre
                data.append(Camembert(
                    titre="Répartition par genre",
                    labels=["Garçons", "Filles"],
                    valeurs=[resultats["M"], resultats["F"]],
                    couleurs=["rgba(54, 162, 235, 0.5)", "rgba(255, 99, 132, 0.5)"],
                ))


            # ---------------------------- INDIVIDUS : Age -------------------------------
            if rubrique == "individus_age":

                if presents:
                    today = presents[0]
                else:
                    today = None

                # Calcul des âges
                dict_ages = {}
                for individu in Individu.objects.filter(condition).distinct():
                    age = individu.Get_age(today)
                    dict_ages.setdefault(age, 0)
                    dict_ages[age] += 1
                liste_ages = [(age, nbre) for age, nbre in dict_ages.items() if age]
                liste_ages = sorted(liste_ages, key=operator.itemgetter(0))

                # Afficher les ages inconnus
                if None in dict_ages:
                    data.append(Texte(texte="Remarque : La date de naissance n'a pas été renseignée pour %d individus." % dict_ages[None]))

                # Tableau : Répartition par âge
                data.append(Tableau(
                    titre="Répartition par âge",
                    colonnes=["Age", "Nombre d'individus"],
                    lignes=liste_ages
                ))

                # Chart : Répartition par âge
                data.append(Histogramme(titre="Répartition par âge", type_chart="bar",
                    labels=[age for age, nbre in liste_ages],
                    valeurs=[nbre for age, nbre in liste_ages],
                ))

                # Calcul des années de naissance
                individus = Individu.objects.filter(condition).values_list('date_naiss__year').annotate(nbre=Count('idindividu', distinct=True)).order_by('date_naiss__year')

                # Tableau : Répartition par âge
                data.append(Tableau(
                    titre="Répartition par année de naissance",
                    colonnes=["Année", "Nombre d'individus"],
                    lignes=[(age, nbre) for age, nbre in individus if age],
                ))

                # Chart : Répartition par âge
                data.append(Histogramme(titre="Répartition par année de naissance", type_chart="bar",
                    labels=[annee for annee, nbre in individus if annee],
                    valeurs=[nbre for annee, nbre in individus if annee],
                ))

            # ---------------------------- INDIVIDUS : Coordonnées -------------------------------
            if rubrique == "individus_coordonnees":

                # Tableau : Répartition des individus par ville de résidence
                individus = Individu.objects.filter(condition).values_list("ville_resid").annotate(nbre=Count("idindividu", distinct=True)).order_by("-nbre")
                data.append(Tableau(
                    titre="Répartition des individus par ville de résidence",
                    colonnes=["Ville de résidence", "Nombre d'individus"],
                    lignes=[(item[0] if item[0] else "Ville non renseignée", item[1]) for item in individus]
                ))

                # Camembert : Répartition des individus par ville de résidence
                data.append(Camembert(
                    titre="Répartition des individus par ville de résidence",
                    labels=[item[0] if item[0] else "Ville non renseignée" for item in individus],
                    valeurs=[item[1] for item in individus],
                ))


            # ---------------------------- INDIVIDUS : Scolarité -------------------------------
            if rubrique == "individus_scolarite":

                nbre_individus_total = Individu.objects.filter(condition).distinct().count()

                # Recherche de l'école des individus
                condition_temp = Q(scolarite__date_debut__lte=presents[0], scolarite__date_fin__gte=presents[0])
                individus = list(Individu.objects.filter(condition, condition_temp).values_list("scolarite__ecole__nom").annotate(nbre=Count("idindividu", distinct=True)).order_by("nbre"))
                nbre_individus_avec_scolarite = 0
                for item in individus:
                    nbre_individus_avec_scolarite += item[1]
                nbre_individus_sans_scolarite = nbre_individus_total - nbre_individus_avec_scolarite
                if nbre_individus_sans_scolarite:
                    individus.insert(0, ("Ecole non spécifiée", nbre_individus_sans_scolarite))

                # Tableau : Répartition des individus par école
                data.append(Tableau(
                    titre="Répartition des individus par école",
                    colonnes=["Ecole", "Nombre d'individus"],
                    lignes=[(item[0], item[1]) for item in individus]
                ))

                # Camembert : Répartition des individus par école
                data.append(Camembert(
                    titre="Répartition des individus par école",
                    labels=[item[0] for item in individus],
                    valeurs=[item[1] for item in individus],
                ))

                # Recherche du niveau des individus
                condition_temp = Q(scolarite__date_debut__lte=presents[0], scolarite__date_fin__gte=presents[0], scolarite__niveau__nom__isnull=False)
                individus = list(Individu.objects.filter(condition, condition_temp).values_list("scolarite__niveau__nom").annotate(nbre=Count("idindividu", distinct=True)).order_by("nbre"))
                nbre_individus_avec_scolarite = 0
                for item in individus:
                    nbre_individus_avec_scolarite += item[1]
                nbre_individus_sans_scolarite = nbre_individus_total - nbre_individus_avec_scolarite
                if nbre_individus_sans_scolarite:
                    individus.insert(0, ("Niveau non spécifié", nbre_individus_sans_scolarite))

                # Tableau : Répartition des individus par niveau
                data.append(Tableau(
                    titre="Répartition des individus par niveau",
                    colonnes=["Niveau scolaire", "Nombre d'individus"],
                    lignes=[(item[0], item[1]) for item in individus]
                ))

                # Camembert : Répartition des individus par niveau
                data.append(Camembert(
                    titre="Répartition des individus par niveau",
                    labels=[item[0] for item in individus],
                    valeurs=[item[1] for item in individus],
                ))


            # ---------------------------- INDIVIDUS : Profession -------------------------------
            if rubrique == "individus_profession":

                # Tableau : Répartition des individus par catégorie socio-professionnelle
                individus = Individu.objects.filter(condition).values_list("categorie_travail__nom").annotate(nbre=Count("idindividu", distinct=True)).order_by("-nbre")
                data.append(Tableau(
                    titre="Répartition des individus par catégorie socio-professionnelle",
                    colonnes=["Catégorie", "Nombre d'individus"],
                    lignes=[(item[0] if item[0] else "Catégorie non renseignée", item[1]) for item in individus]
                ))

                # Camembert : Répartition des individus par catégorie socio-professionnelle
                data.append(Camembert(
                    titre="Répartition des individus par catégorie socio-professionnelle",
                    labels=[item[0] if item[0] else "Catégorie non renseignée" for item in individus],
                    valeurs=[item[1] for item in individus],
                ))



            # ================================ FAMILLES ====================================

            if rubrique.startswith("familles"):
                if presents:
                    condition = Q(rattachement__individu__consommation__activite__in=liste_activites, rattachement__individu__consommation__date__gte=presents[0], rattachement__individu__consommation__date__lte=presents[1], rattachement__individu__consommation__etat__in=("present", "reservation"))
                else:
                    condition = Q(rattachement__individu__inscription__activite__in=liste_activites)

            # ---------------------------- FAMILLES : Nombre -------------------------------
            if rubrique == "familles_nombre":

                # Texte : Nombre d'individus total
                data.append(Texte(texte="%d familles dont au moins un membre est %s." % (Famille.objects.filter(condition).distinct().count(), "présent" if presents else "inscrit")))

                # Tableau : Répartition des familles par activité
                familles = Famille.objects.filter(condition).values_list("rattachement__individu__%s__activite__nom" % ("consommation" if presents else "inscription")).annotate(nbre=Count("idfamille", distinct=True)).order_by("-nbre")
                data.append(Tableau(
                    titre="Répartition du nombre de familles par activité",
                    colonnes=["Activité", "Nombre de familles"],
                    lignes=[(item[0], item[1]) for item in familles]
                ))

                # Chart : Evolution du nombre de familles - comparatif par période
                if presents:
                    liste_periodes= Calcule_periodes_comparatives(parametres, presents, liste_activites)
                    if liste_periodes:
                        liste_labels, liste_valeurs = [], []
                        for dict_periode in liste_periodes:
                            condition_temp = Q(rattachement__individu__consommation__activite__in=liste_activites, rattachement__individu__consommation__date__gte=dict_periode["date_debut"], rattachement__individu__consommation__date__lte=dict_periode["date_fin"], rattachement__individu__consommation__etat__in=("present", "reservation"))
                            liste_labels.append(dict_periode["label"])
                            liste_valeurs.append(Famille.objects.filter(condition_temp).distinct().count())
                        data.append(Histogramme(titre="Evolution du nombre des familles", type_chart="bar", labels=liste_labels, valeurs=liste_valeurs))

                # Chart : Nombre de familles par date
                if presents:
                    familles = Famille.objects.filter(condition).values_list('rattachement__individu__consommation__date').annotate(nbre=Count('idfamille', distinct=True)).order_by('rattachement__individu__consommation__date')
                    data.append(Histogramme(
                        titre="Nombre familles par date", type_chart="line",
                        labels=[utils_dates.ConvertDateToFR(date) for date, nbre in familles],
                        valeurs=[nbre for date, nbre in familles],
                    ))


            # ---------------------------- FAMILLES : Caisse -------------------------------
            if rubrique == "familles_caisse":

                familles = Famille.objects.filter(condition).values_list("caisse__nom").annotate(nbre=Count("idfamille", distinct=True)).order_by("-nbre")

                # Tableau : Répartition des familles par caisse
                data.append(Tableau(
                    titre="Répartition des familles par caisse",
                    colonnes=["Caisse", "Nombre de familles"],
                    lignes=[(item[0] if item[0] else "Caisse non renseignée", item[1]) for item in familles]
                ))

                # Camembert : Répartition des familles par caisse
                data.append(Camembert(
                    titre="Répartition des familles par caisse",
                    labels=[item[0] if item[0] else "Caisse non renseignée" for item in familles],
                    valeurs=[item[1] for item in familles],
                ))

            # ---------------------------- FAMILLES : Composition -------------------------------

            if rubrique == "familles_composition":
                familles = Individu.objects.filter(condition).values_list("inscription__famille").annotate(nbre=Count("idindividu", distinct=True)).order_by("nbre")
                dict_familles = {}
                for item in familles:
                    dict_familles.setdefault(item[1], 0)
                    dict_familles[item[1]] += 1
                familles = [(key, valeur) for key, valeur in dict_familles.items()]

                # Tableau : Composition des familles
                data.append(Tableau(titre="Composition des familles",
                    colonnes=["Nombre de membres", "Nombre de familles"],
                    lignes=[(item[0], item[1]) for item in familles]))

                # Camembert : Composition des familles
                data.append(Camembert(titre="Composition des familles",
                    labels=[item[0] for item in familles],
                    valeurs=[item[1] for item in familles], ))





        return data