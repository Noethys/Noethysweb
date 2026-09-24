# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, random, datetime, calendar, operator
from django.views.generic import TemplateView
from django.db.models import Q, Count, Sum, F, Max, Min
from django.db.models.functions import ExtractYear
from core.views.base import CustomView
from core.models import Activite, Consommation, Inscription, Famille, Individu, Vacance, Cotisation, LISTE_MOIS, \
    Historique, Quotient, Rattachement, Prestation, Facture, Reglement, Rappel, LISTE_ETATS_CONSO
from core.utils import utils_dates
from outils.forms.statistiques import Formulaire


class Element():
    def __init__(self, *args, **kwargs):
        self.id = random.randint(1, 100000)
        self.categorie = ""


class Titre(Element):
    def __init__(self, texte=""):
        Element.__init__(self)
        self.categorie = "titre"
        self.texte = texte.upper()


class Texte(Element):
    def __init__(self, texte=""):
        Element.__init__(self)
        self.categorie = "texte"
        self.texte = texte


class Espace(Element):
    def __init__(self, hauteur=30):
        Element.__init__(self)
        self.categorie = "espace"
        self.hauteur = hauteur


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
    def __init__(self, titre="", labels=[], type_chart="line", valeurs=[], chronologie=None):
        Element.__init__(self)
        self.categorie = "histogramme"
        self.type_chart = type_chart # "line" ou "bar"
        self.titre = titre
        self.labels = labels
        self.valeurs = valeurs
        self.chronologie = chronologie # "date"


def Calcule_periodes_comparatives_generique(parametres={}, presents=None, dates_extremes=(None, None)):
    """ Version générique : calcule les périodes comparatives à partir d'un couple (date_min, date_max)
        fourni par l'appelant, quel que soit le modèle d'origine (Consommation, Prestation, Facture, etc.) """
    liste_periodes = []
    date_min, date_max = dates_extremes
    if date_min and date_max:

        if parametres["condition"] == "VACANCES":
            for vacance in Vacance.objects.filter(nom=parametres["vacances"], date_debut__gte=date_min, date_fin__lte=date_max).order_by("date_debut"):
                liste_periodes.append({"date_debut": vacance.date_debut, "date_fin": vacance.date_fin, "label": "%s %d" % (parametres["vacances"], vacance.annee)})

        if parametres["condition"] == "MOIS":
            for annee in range(date_min.year, date_max.year + 1):
                liste_periodes.append(
                    {"date_debut": datetime.date(annee, int(parametres["mois"]), 1),
                     "date_fin": datetime.date(annee, int(parametres["mois"]), calendar.monthrange(annee, int(parametres["mois"]))[1]),
                     "label": "%s %d" % (LISTE_MOIS[int(parametres["mois"]) - 1][1], annee)})

        if parametres["condition"] == "ANNEE":
            for annee in range(date_min.year, date_max.year + 1):
                liste_periodes.append({"date_debut": datetime.date(annee, 1, 1), "date_fin": datetime.date(annee, 12, 31), "label": "Année %d" % annee})

        if parametres["condition"] == "PERIODE":
            if presents[0].year == presents[1].year:
                for annee in range(date_min.year, date_max.year + 1):
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


def Calcule_periodes_comparatives(parametres={}, presents=None, liste_activites=[]):
    """ Version historique, basée sur les dates extrêmes des consommations des activités sélectionnées """
    dates_extremes = Consommation.objects.filter(activite__in=liste_activites, etat__in=parametres["etats"]).aggregate(Min('date'), Max('date'))
    return Calcule_periodes_comparatives_generique(parametres, presents, (dates_extremes["date__min"], dates_extremes["date__max"]))


class View(CustomView, TemplateView):
    menu_code = "statistiques"
    template_name = "outils/statistiques.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Statistiques"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form_parametres=form))
        context = {
            "form_parametres": form,
            "data": self.Get_data(parametres=form.cleaned_data)
        }
        return self.render_to_response(self.get_context_data(**context))

    def Get_data(self, parametres={}):
        data = []
        presents = None
        inscrits_periode = None

        if parametres:
            for rubrique in parametres["rubriques"]:

                # Activités
                param_activites = json.loads(parametres["activites"])
                if param_activites["type"] == "groupes_activites":
                    liste_activites = Activite.objects.filter(groupes_activites__in=param_activites["ids"])
                if param_activites["type"] == "activites":
                    liste_activites = Activite.objects.filter(pk__in=param_activites["ids"])

                # Condition
                if parametres["condition"] == "ANNEE":
                    presents = (datetime.date(parametres["annee"], 1, 1),
                                datetime.date(parametres["annee"], 12, 31))
                if parametres["condition"] == "MOIS":
                    presents = (datetime.date(parametres["annee"], int(parametres["mois"]), 1),
                                datetime.date(parametres["annee"], int(parametres["mois"]), calendar.monthrange(parametres["annee"], int(parametres["mois"]))[1]))
                if parametres["condition"] == "VACANCES":
                    vacance = Vacance.objects.filter(nom=parametres["vacances"], annee=parametres["annee"]).first()
                    presents = (vacance.date_debut, vacance.date_fin)
                if parametres["condition"] == "PERIODE":
                    presents = utils_dates.ConvertDateRangePicker(parametres["periode"])
                if parametres["condition"] == "INSCRITS_PERIODE":
                    inscrits_periode = utils_dates.ConvertDateRangePicker(parametres["periode"])
                if parametres["condition"] == "ADHERENTS_PERIODE":
                    periode = utils_dates.ConvertDateRangePicker(parametres["periode"])
                    liste_cotisations = Cotisation.objects.filter(date_debut__lte=periode[1], date_fin__gte=periode[0], type_cotisation__in=parametres["types_cotisations"])

                # ================================ INDIVIDUS ====================================

                if rubrique.startswith("individus"):
                    if parametres["condition"] in ("ANNEE", "MOIS", "VACANCES", "PERIODE"):
                        condition = Q(consommation__activite__in=liste_activites, consommation__date__gte=presents[0], consommation__date__lte=presents[1], consommation__etat__in=parametres["etats"])
                    if parametres["condition"] in ("INSCRITS", "INSCRITS_PERIODE"):
                        condition = Q(inscription__activite__in=liste_activites)
                        if inscrits_periode:
                            condition &= Q(inscription__date_debut__gte=inscrits_periode[0], inscription__date_debut__lte=inscrits_periode[1])
                    if parametres["condition"] == "ADHERENTS_PERIODE":
                        liste_individus, liste_familles = [], []
                        for cotisation in liste_cotisations:
                            if cotisation.individu_id:
                                # On prend en compte les individus des cotisations individuelles
                                liste_individus.append(cotisation.individu_id)
                            else:
                                liste_familles.append(cotisation.famille_id)
                        if liste_familles:
                            # On prend en compte tous les membres de la famille si cotisation famille
                            liste_individus += [r.individu_id for r in Rattachement.objects.filter(famille_id__in=liste_familles, categorie__in=(1, 2))]
                        condition = Q(pk__in=liste_individus)

                # ---------------------------- INDIVIDUS : Nombre -------------------------------
                if rubrique == "individus_nombre":
                    data.append(Titre(texte="Nombre d'individus"))

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
                                condition_temp = Q(consommation__activite__in=liste_activites, consommation__date__gte=dict_periode["date_debut"], consommation__date__lte=dict_periode["date_fin"], consommation__etat__in=parametres["etats"])
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
                    data.append(Titre(texte="Genre des individus"))

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
                    data.append(Titre(texte="Age des individus"))

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
                    annees_naiss = {}
                    for individu in Individu.objects.filter(condition).distinct():
                        if individu.date_naiss:
                            annees_naiss.setdefault(individu.date_naiss.year, 0)
                            annees_naiss[individu.date_naiss.year] += 1
                    liste_annees_naiss = [(annee, nbre) for annee, nbre in annees_naiss.items()]
                    liste_annees_naiss.sort()

                    # Tableau : Répartition par année de naissance
                    data.append(Tableau(
                        titre="Répartition par année de naissance",
                        colonnes=["Année", "Nombre d'individus"],
                        lignes=[(annee, nbre) for annee, nbre in liste_annees_naiss],
                    ))

                    # Chart : Répartition par année de naissance
                    data.append(Histogramme(titre="Répartition par année de naissance", type_chart="bar",
                        labels=[annee for annee, nbre in liste_annees_naiss],
                        valeurs=[nbre for annee, nbre in liste_annees_naiss],
                    ))

                # ---------------------------- INDIVIDUS : Coordonnées -------------------------------
                if rubrique == "individus_coordonnees":
                    data.append(Titre(texte="Coordonnées des individus"))

                    # Tableau : Répartition des individus par ville de résidence
                    villes = {}
                    for ville, nbre in Individu.objects.filter(condition).values_list("ville_resid").annotate(nbre=Count("idindividu", distinct=True)).order_by("ville_resid"):
                        villes.setdefault(ville, 0)
                        villes[ville] += nbre
                    liste_villes = [(ville, nbre) for ville, nbre in villes.items()]

                    data.append(Tableau(
                        titre="Répartition des individus par ville de résidence",
                        colonnes=["Ville de résidence", "Nombre d'individus"],
                        lignes=[(item[0] if item[0] else "Ville non renseignée", item[1]) for item in liste_villes]
                    ))

                    # Camembert : Répartition des individus par ville de résidence
                    data.append(Camembert(
                        titre="Répartition des individus par ville de résidence",
                        labels=[item[0] if item[0] else "Ville non renseignée" for item in liste_villes],
                        valeurs=[item[1] for item in liste_villes],
                    ))

                    # Tableau : Répartition des individus par secteur
                    secteurs = {}
                    for secteur, nbre in Individu.objects.select_related("secteur").filter(condition).values_list("secteur__nom").annotate(nbre=Count("idindividu", distinct=True)).order_by("secteur__nom"):
                        secteurs.setdefault(secteur, 0)
                        secteurs[secteur] += nbre
                    liste_secteurs = [(secteur, nbre) for secteur, nbre in secteurs.items()]

                    data.append(Tableau(
                        titre="Répartition des individus par secteur",
                        colonnes=["Secteur", "Nombre d'individus"],
                        lignes=[(item[0] if item[0] else "Secteur non renseigné", item[1]) for item in liste_secteurs]
                    ))

                    # Camembert : Répartition des individus par secteur
                    data.append(Camembert(
                        titre="Répartition des individus par secteur",
                        labels=[item[0] if item[0] else "Secteur non renseigné" for item in liste_secteurs],
                        valeurs=[item[1] for item in liste_secteurs],
                    ))

                # ---------------------------- INDIVIDUS : Scolarité -------------------------------
                if rubrique == "individus_scolarite":
                    data.append(Titre(texte="Scolarité des individus"))

                    date_reference = presents[0] if presents else datetime.date.today()
                    nbre_individus_total = Individu.objects.filter(condition).distinct().count()

                    # Recherche de l'école des individus

                    condition_temp = Q(scolarite__date_debut__lte=date_reference, scolarite__date_fin__gte=date_reference)
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
                    condition_temp = Q(scolarite__date_debut__lte=date_reference, scolarite__date_fin__gte=date_reference, scolarite__niveau__nom__isnull=False)
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
                    data.append(Titre(texte="Profession des individus"))

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


                # ---------------------------- INDIVIDUS : Situation familiale -------------------------------
                if rubrique == "individus_situation_familiale":
                    data.append(Titre(texte="Situation familiale des parents"))

                    dict_labels = dict(Individu._meta.get_field("situation_familiale").choices)
                    individus = Individu.objects.filter(condition).values_list("situation_familiale").annotate(nbre=Count("idindividu", distinct=True)).order_by("-nbre")

                    data.append(Tableau(
                        titre="Répartition par situation familiale",
                        colonnes=["Situation familiale", "Nombre d'individus"],
                        lignes=[(dict_labels.get(item[0], "Non renseignée"), item[1]) for item in individus]
                    ))
                    data.append(Camembert(
                        titre="Répartition par situation familiale",
                        labels=[dict_labels.get(item[0], "Non renseignée") for item in individus],
                        valeurs=[item[1] for item in individus],
                    ))


                # ---------------------------- INDIVIDUS : Type de garde -------------------------------
                if rubrique == "individus_type_garde":
                    data.append(Titre(texte="Type de garde"))

                    dict_labels = dict(Individu._meta.get_field("type_garde").choices)
                    individus = Individu.objects.filter(condition).values_list("type_garde").annotate(nbre=Count("idindividu", distinct=True)).order_by("-nbre")

                    data.append(Tableau(
                        titre="Répartition par type de garde",
                        colonnes=["Type de garde", "Nombre d'individus"],
                        lignes=[(dict_labels.get(item[0], "Non renseigné"), item[1]) for item in individus]
                    ))
                    data.append(Camembert(
                        titre="Répartition par type de garde",
                        labels=[dict_labels.get(item[0], "Non renseigné") for item in individus],
                        valeurs=[item[1] for item in individus],
                    ))


                # ---------------------------- INDIVIDUS : Régime alimentaire -------------------------------
                if rubrique == "individus_regime_alimentaire":
                    data.append(Titre(texte="Régimes alimentaires déclarés"))

                    individus = Individu.objects.filter(condition).values_list("regimes_alimentaires__nom").annotate(nbre=Count("idindividu", distinct=True)).order_by("-nbre")

                    data.append(Tableau(
                        titre="Répartition par régime alimentaire déclaré",
                        colonnes=["Régime alimentaire", "Nombre d'individus"],
                        lignes=[(item[0] if item[0] else "Aucun régime particulier déclaré", item[1]) for item in individus]
                    ))
                    data.append(Camembert(
                        titre="Répartition par régime alimentaire déclaré",
                        labels=[item[0] if item[0] else "Aucun régime particulier déclaré" for item in individus],
                        valeurs=[item[1] for item in individus],
                    ))


                # ================================ FAMILLES ====================================

                liste_idfamille = []
                inscriptions = []
                if rubrique.startswith("familles"):
                    if parametres["condition"] in ("ANNEE", "MOIS", "VACANCES", "PERIODE"):
                        condition = Q(activite__in=liste_activites, date__gte=presents[0], date__lte=presents[1], etat__in=parametres["etats"])
                        condition = Q(pk__in=list({c.inscription_id: True for c in Consommation.objects.filter(condition)}.keys()))

                    if parametres["condition"] in ("INSCRITS", "INSCRITS_PERIODE"):
                        condition = Q(activite__in=liste_activites)
                        if inscrits_periode:
                            condition &= Q(date_debut__gte=inscrits_periode[0], date_debut__lte=inscrits_periode[1])

                    if parametres["condition"] in ("ANNEE", "MOIS", "VACANCES", "PERIODE", "INSCRITS", "INSCRITS_PERIODE"):
                        inscriptions = Inscription.objects.select_related("activite").filter(condition)
                        liste_idfamille = list({inscription.famille_id: True for inscription in inscriptions}.keys())

                    if parametres["condition"] == "ADHERENTS_PERIODE":
                        liste_idfamille = list({cotisation.famille_id: True for cotisation in liste_cotisations}.keys())

                # ---------------------------- FAMILLES : Nombre -------------------------------
                if rubrique == "familles_nombre":
                    data.append(Titre(texte="Nombre de familles"))

                    # Texte : Nombre d'individus total
                    data.append(Texte(texte="%d familles dont au moins un membre est %s." % (len(liste_idfamille), "présent" if presents else "inscrit")))

                    # Tableau : Répartition des familles par activité
                    if inscriptions:
                        familles = inscriptions.values_list("activite__nom").annotate(nbre=Count("famille_id", distinct=True)).order_by("-nbre")
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
                                liste_labels.append(dict_periode["label"])
                                condition = Q(activite__in=liste_activites, date__gte=dict_periode["date_debut"], date__lte=dict_periode["date_fin"], etat__in=parametres["etats"])
                                liste_valeurs.append(len({c.inscription.famille_id: True for c in Consommation.objects.select_related("inscription").filter(condition) if c.inscription}))

                            data.append(Histogramme(titre="Evolution du nombre des familles", type_chart="bar", labels=liste_labels, valeurs=liste_valeurs))

                    # Chart : Nombre de familles par date
                    if presents:
                        condition = Q(activite__in=liste_activites, date__gte=presents[0], date__lte=presents[1], etat__in=parametres["etats"])
                        familles = Consommation.objects.filter(condition).values_list("date").annotate(nbre=Count("inscription__famille_id", distinct=True)).order_by("date")
                        data.append(Histogramme(
                            titre="Nombre familles par date", type_chart="line",
                            labels=[utils_dates.ConvertDateToFR(date) for date, nbre in familles],
                            valeurs=[nbre for date, nbre in familles],
                        ))


                # ---------------------------- FAMILLES : Caisse -------------------------------
                if rubrique == "familles_caisse":
                    data.append(Titre(texte="Caisse des familles"))

                    familles = Famille.objects.filter(pk__in=liste_idfamille).values_list("caisse__nom").annotate(nbre=Count("idfamille", distinct=True)).order_by("-nbre")

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
                    data.append(Titre(texte="Composition des familles"))

                    # Composition des familles des membres qui fréquentent les activités sélectionnées
                    nbre_membres_familles = {item["famille_id"]: item["nbre_membres"] for item in Rattachement.objects.values("famille_id") \
                                            .filter(categorie__in=(1, 2), famille_id__in=liste_idfamille).annotate(nbre_membres=Count("pk"))}
                    dict_familles = {}
                    for nbre_membres in nbre_membres_familles.values():
                        dict_familles.setdefault(nbre_membres, 0)
                        dict_familles[nbre_membres] += 1
                    familles = [(key, valeur) for key, valeur in dict_familles.items()]

                    # Tableau : Composition des familles
                    data.append(Tableau(titre="Composition des familles",
                        colonnes=["Nombre total de membres", "Nombre de familles"],
                        lignes=[(item[0], item[1]) for item in familles]))

                    # Camembert : Composition des familles
                    data.append(Camembert(titre="Composition des familles",
                        labels=[item[0] for item in familles],
                        valeurs=[item[1] for item in familles], ))

                    # Membres de la famille qui fréquentent les activités sélectionnées
                    if inscriptions:
                        familles = Individu.objects.filter(pk__in=[inscription.individu_id for inscription in inscriptions]).values_list("inscription__famille").annotate(nbre=Count("idindividu", distinct=True)).order_by("nbre")
                        dict_familles = {}
                        for item in familles:
                            dict_familles.setdefault(item[1], 0)
                            dict_familles[item[1]] += 1
                        familles = [(key, valeur) for key, valeur in dict_familles.items()]

                        # Tableau : Membres de la famille qui fréquentent les activités sélectionnées
                        data.append(Tableau(titre="Membres de la famille qui fréquentent les activités sélectionnées",
                            colonnes=["Nombre de membres", "Nombre de familles"],
                            lignes=[(item[0], item[1]) for item in familles]))

                        # Camembert : Membres de la famille qui fréquentent les activités sélectionnées
                        data.append(Camembert(titre="Membres de la famille qui fréquentent les activités sélectionnées",
                            labels=[item[0] for item in familles],
                            valeurs=[item[1] for item in familles], ))

                # ---------------------------- FAMILLES : QF -------------------------------

                if rubrique == "familles_qf":
                    data.append(Titre(texte="Quotients familiaux des familles"))

                    # Récupération des tranches de qf
                    dict_tranches = {None: 0}
                    try:
                        for tranche in parametres["tranches_qf"].split(";"):
                            qf_min, qf_max = tranche.split("-")
                            dict_tranches[(int(qf_min), int(qf_max))] = 0
                    except:
                        data.append(Texte("Erreur : Les tranches de QF saisies semblent erronées."))

                    # Recherche des qf des familles
                    familles = Famille.objects.filter(pk__in=liste_idfamille).distinct()
                    condition_qf = Q(famille__in=familles, date_debut__lte=presents[1], date_fin__gte=presents[0]) if presents else Q(famille__in=familles)
                    dict_quotients = {quotient.famille_id: quotient.quotient for quotient in Quotient.objects.filter(condition_qf).order_by("date_debut")}

                    # Regroupement des qf par tranche
                    for famille in familles:
                        quotient = dict_quotients.get(famille.pk, None)
                        found = False
                        if quotient:
                            for tranche, nbre in dict_tranches.items():
                                if tranche and tranche[0] <= quotient <= tranche[1]:
                                    dict_tranches[tranche] += 1
                                    found = True
                        if not found:
                            dict_tranches[None] += 1

                    def Formate_tranche(tranche):
                        return "%d - %d" % tranche if tranche else "Autre ou inconnu"

                    # Tableau : QF des familles
                    data.append(Tableau(titre="Quotients familiaux des familles",
                        colonnes=["Tranches de QF", "Nombre de familles"],
                        lignes=[(Formate_tranche(tranche), nbre) for tranche, nbre in dict_tranches.items()]))

                    # Camembert : QF des familles
                    data.append(Camembert(titre="Quotients familiaux des familles",
                        labels=[Formate_tranche(tranche) for tranche, nbre in dict_tranches.items()],
                        valeurs=[nbre for tranche, nbre in dict_tranches.items()]))

                # ---------------------------- FAMILLES : Secteur -------------------------------

                if rubrique == "familles_secteur":
                    data.append(Titre(texte="Répartition des familles par secteur"))

                    familles = Famille.objects.filter(pk__in=liste_idfamille).values_list("secteur__nom").annotate(nbre=Count("idfamille", distinct=True)).order_by("-nbre")

                    data.append(Tableau(titre="Répartition des familles par secteur",
                        colonnes=["Secteur", "Nombre de familles"],
                        lignes=[(item[0] if item[0] else "Secteur non renseigné", item[1]) for item in familles]))
                    data.append(Camembert(titre="Répartition des familles par secteur",
                        labels=[item[0] if item[0] else "Secteur non renseigné" for item in familles],
                        valeurs=[item[1] for item in familles]))

                # ---------------------------- FAMILLES : Régime social -------------------------------

                if rubrique == "familles_regime_social":
                    data.append(Titre(texte="Répartition des familles par régime social"))

                    familles = Famille.objects.filter(pk__in=liste_idfamille).values_list("caisse__regime__nom").annotate(nbre=Count("idfamille", distinct=True)).order_by("-nbre")

                    data.append(Tableau(titre="Répartition des familles par régime social",
                        colonnes=["Régime social", "Nombre de familles"],
                        lignes=[(item[0] if item[0] else "Non renseigné", item[1]) for item in familles]))
                    data.append(Camembert(titre="Répartition des familles par régime social",
                        labels=[item[0] if item[0] else "Non renseigné" for item in familles],
                        valeurs=[item[1] for item in familles]))

                # ---------------------------- FAMILLES : Ancienneté -------------------------------

                if rubrique == "familles_anciennete":
                    data.append(Titre(texte="Ancienneté des familles"))

                    familles = Famille.objects.filter(pk__in=liste_idfamille).annotate(annee=ExtractYear("date_creation")).values_list("annee").annotate(nbre=Count("idfamille", distinct=True)).order_by("annee")

                    data.append(Tableau(titre="Répartition des familles par année de création du dossier",
                        colonnes=["Année de création", "Nombre de familles"],
                        lignes=[(item[0], item[1]) for item in familles]))
                    data.append(Histogramme(titre="Répartition des familles par année de création du dossier", type_chart="bar",
                        labels=[item[0] for item in familles],
                        valeurs=[item[1] for item in familles]))

                # ---------------------------- CONSOMMATIONS : Nombre -------------------------------

                if rubrique == "consommations_nombre":
                    data.append(Titre(texte="Nombre de consommations"))

                    if not presents:
                        data.append(Texte(texte="Donnée accessible uniquement avec le mode Présents."))
                    else:
                        conso = Consommation.objects.filter(activite__in=liste_activites, date__range=presents, etat__in=parametres["etats"])

                        # Texte : Nombre total
                        data.append(Texte(texte="%d consommations enregistrées sur la période sélectionnée." % conso.count()))

                        # Tableau et camembert : Répartition par activité
                        resultats = conso.values_list("activite__nom").annotate(nbre=Count("idconso")).order_by("-nbre")
                        data.append(Tableau(titre="Répartition des consommations par activité",
                            colonnes=["Activité", "Nombre de consommations"],
                            lignes=[(item[0], item[1]) for item in resultats]))
                        data.append(Camembert(titre="Répartition des consommations par activité",
                            labels=[item[0] for item in resultats],
                            valeurs=[item[1] for item in resultats]))

                # ---------------------------- CONSOMMATIONS : Etats -------------------------------

                if rubrique == "consommations_etats":
                    data.append(Titre(texte="Etats des consommations"))

                    if not presents:
                        data.append(Texte(texte="Donnée accessible uniquement avec le mode Présents."))
                    else:
                        dict_labels_etats = dict(LISTE_ETATS_CONSO)
                        resultats = Consommation.objects.filter(activite__in=liste_activites, date__range=presents).values_list("etat").annotate(nbre=Count("idconso")).order_by("-nbre")

                        data.append(Tableau(titre="Répartition des consommations par état",
                            colonnes=["Etat", "Nombre de consommations"],
                            lignes=[(dict_labels_etats.get(item[0], item[0] or "Non renseigné"), item[1]) for item in resultats]))
                        data.append(Camembert(titre="Répartition des consommations par état",
                            labels=[dict_labels_etats.get(item[0], item[0] or "Non renseigné") for item in resultats],
                            valeurs=[item[1] for item in resultats]))

                # ---------------------------- CONSOMMATIONS : Absentéisme -------------------------------

                if rubrique == "consommations_absenteisme":
                    data.append(Titre(texte="Absentéisme"))

                    if not presents:
                        data.append(Texte(texte="Donnée accessible uniquement avec le mode Présents."))
                    else:
                        conso = Consommation.objects.filter(activite__in=liste_activites, date__range=presents, etat__in=("present", "absentj", "absenti"))
                        nbre_total = conso.count()
                        nbre_absentj = conso.filter(etat="absentj").count()
                        nbre_absenti = conso.filter(etat="absenti").count()
                        nbre_present = nbre_total - nbre_absentj - nbre_absenti
                        taux = round((nbre_absentj + nbre_absenti) / nbre_total * 100, 1) if nbre_total else 0

                        data.append(Texte(texte="Taux d'absentéisme : %s%% (%d absences sur %d présences prévues)." % (taux, nbre_absentj + nbre_absenti, nbre_total)))
                        data.append(Tableau(titre="Répartition présents / absents",
                            colonnes=["Statut", "Nombre"],
                            lignes=[("Présents", nbre_present), ("Absences justifiées", nbre_absentj), ("Absences injustifiées", nbre_absenti)]))
                        data.append(Camembert(titre="Répartition présents / absents",
                            labels=["Présents", "Absences justifiées", "Absences injustifiées"],
                            valeurs=[nbre_present, nbre_absentj, nbre_absenti],
                            couleurs=["rgba(75, 192, 100, 0.5)", "rgba(255, 206, 86, 0.5)", "rgba(255, 99, 132, 0.5)"]))

                # ---------------------------- CONSOMMATIONS : Groupes -------------------------------

                if rubrique == "consommations_groupes":
                    data.append(Titre(texte="Répartition par groupe"))

                    if not presents:
                        data.append(Texte(texte="Donnée accessible uniquement avec le mode Présents."))
                    else:
                        resultats = Consommation.objects.filter(activite__in=liste_activites, date__range=presents, etat__in=parametres["etats"]).values_list("groupe__nom").annotate(nbre=Count("idconso")).order_by("-nbre")
                        data.append(Tableau(titre="Répartition des consommations par groupe",
                            colonnes=["Groupe", "Nombre de consommations"],
                            lignes=[(item[0] if item[0] else "Groupe non renseigné", item[1]) for item in resultats]))
                        data.append(Camembert(titre="Répartition des consommations par groupe",
                            labels=[item[0] if item[0] else "Groupe non renseigné" for item in resultats],
                            valeurs=[item[1] for item in resultats]))

                # ---------------------------- CONSOMMATIONS : Evénements -------------------------------

                if rubrique == "consommations_evenements":
                    data.append(Titre(texte="Consommations liées à des événements"))

                    if not presents:
                        data.append(Texte(texte="Donnée accessible uniquement avec le mode Présents."))
                    else:
                        resultats = Consommation.objects.filter(activite__in=liste_activites, date__range=presents, etat__in=parametres["etats"], evenement__isnull=False).values_list("evenement__nom").annotate(nbre=Count("idconso")).order_by("-nbre")
                        if not resultats:
                            data.append(Texte(texte="Aucune consommation liée à un événement sur la période sélectionnée."))
                        else:
                            data.append(Tableau(titre="Répartition des consommations par événement",
                                colonnes=["Evénement", "Nombre de consommations"],
                                lignes=[(item[0], item[1]) for item in resultats]))
                            data.append(Camembert(titre="Répartition des consommations par événement",
                                labels=[item[0] for item in resultats],
                                valeurs=[item[1] for item in resultats]))

                # ---------------------------- CONSOMMATIONS : Saisie -------------------------------

                if rubrique == "consommations_saisie":
                    data.append(Titre(texte="Saisie des consommations"))

                    if not presents:
                        data.append(Texte(texte="Données accessible uniquement avec le mode Présents."))
                    else:

                        # Chart : Dates de saisie des consommations
                        donnees = Consommation.objects.filter(activite__in=liste_activites, date__range=presents).values_list("date_saisie__date").annotate(nbre=Count("idconso", distinct=True)).order_by("date_saisie__date")
                        data.append(Histogramme(titre="Dates de saisie des consommations", type_chart="bar", chronologie="date",
                            labels=[str(date) for date, nbre in donnees],
                            valeurs=[nbre for date, nbre in donnees],
                        ))

                        # Chart : Anticipation des réservations en nombre de jours
                        donnees = Consommation.objects.filter(activite__in=liste_activites, date__range=presents).annotate(jours=F("date_saisie__date") - F("date")).values_list("jours")
                        resultats = {}
                        for delta, in donnees:
                            resultats.setdefault(delta, 0)
                            resultats[delta] += 1
                        donnees = [(nbre_jours, nbre_conso) for nbre_jours, nbre_conso in resultats.items()]
                        donnees.sort()
                        data.append(Histogramme(titre="Anticipation des réservations en nombre de jours", type_chart="bar",
                            labels=[nbre_jours.days for nbre_jours, nbre_conso in donnees],
                            valeurs=[nbre_conso for nbre_jours, nbre_conso in donnees],
                        ))

                        # Chart : Evolution des réservations
                        condition = (Q(titre="Ajout d'une consommation") | Q(titre="Suppression d'une consommation")) & Q(activite__in=liste_activites, date__range=presents)
                        dict_temp = {}
                        for titre, date, nbre in Historique.objects.filter(condition).values_list("titre", "horodatage__date").annotate(nbre=Count("idaction", distinct=True)).order_by("horodatage__date"):
                            dict_temp[date] = dict_temp.get(date, 0) + (-nbre if "Suppression" in titre else nbre)
                        donnees = []
                        x = 0
                        for date, nbre in dict_temp.items():
                            x += nbre
                            donnees.append((date, x))
                        donnees.sort()
                        data.append(Histogramme(
                            titre="Evolution des réservations pour les consommations de la période sélectionnée", type_chart="line", chronologie="date",
                            labels=[str(date) for date, nbre in donnees],
                            valeurs=[nbre for date, nbre in donnees],
                        ))

                # ================================ PRESTATIONS ====================================

                condition_dates_prestations = parametres["condition"] in ("ANNEE", "MOIS", "VACANCES", "PERIODE")

                # ---------------------------- PRESTATIONS : Nombre -------------------------------

                if rubrique == "prestations_nombre":
                    data.append(Titre(texte="Nombre et montant des prestations"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        prestations = Prestation.objects.filter(activite__in=liste_activites, date__range=presents)
                        montant_total = prestations.aggregate(Sum("montant"))["montant__sum"] or 0

                        data.append(Texte(texte="%d prestations enregistrées, pour un montant total de %.2f €." % (prestations.count(), montant_total)))

                        resultats = prestations.values_list("categorie_tarif__nom").annotate(nbre=Count("idprestation"), montant=Sum("montant")).order_by("-montant")
                        data.append(Tableau(titre="Répartition du montant par catégorie de tarif",
                            colonnes=["Catégorie de tarif", "Nombre de prestations", "Montant (€)"],
                            lignes=[(item[0] if item[0] else "Non renseignée", item[1], float(item[2] or 0)) for item in resultats]))

                # ---------------------------- PRESTATIONS : Catégorie -------------------------------

                if rubrique == "prestations_categorie":
                    data.append(Titre(texte="Répartition par catégorie de prestation"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        dict_labels_categorie = dict(Prestation._meta.get_field("categorie").choices)
                        resultats = Prestation.objects.filter(date__range=presents).values_list("categorie").annotate(nbre=Count("idprestation"), montant=Sum("montant")).order_by("-montant")

                        data.append(Tableau(titre="Répartition du montant par catégorie de prestation",
                            colonnes=["Catégorie", "Nombre de prestations", "Montant (€)"],
                            lignes=[(dict_labels_categorie.get(item[0], item[0]), item[1], float(item[2] or 0)) for item in resultats]))
                        data.append(Camembert(titre="Répartition du montant par catégorie de prestation",
                            labels=[dict_labels_categorie.get(item[0], item[0]) for item in resultats],
                            valeurs=[float(item[2] or 0) for item in resultats]))

                # ---------------------------- PRESTATIONS : Activité -------------------------------

                if rubrique == "prestations_activite":
                    data.append(Titre(texte="Répartition du montant des prestations par activité"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        resultats = Prestation.objects.filter(activite__in=liste_activites, date__range=presents).values_list("activite__nom").annotate(montant=Sum("montant")).order_by("-montant")

                        data.append(Tableau(titre="Répartition du montant des prestations par activité",
                            colonnes=["Activité", "Montant (€)"],
                            lignes=[(item[0] if item[0] else "Activité non renseignée", float(item[1] or 0)) for item in resultats]))
                        data.append(Camembert(titre="Répartition du montant des prestations par activité",
                            labels=[item[0] if item[0] else "Activité non renseignée" for item in resultats],
                            valeurs=[float(item[1] or 0) for item in resultats]))

                # ---------------------------- PRESTATIONS : Evolution -------------------------------

                if rubrique == "prestations_evolution":
                    data.append(Titre(texte="Evolution du montant des prestations"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        dates_extremes = Prestation.objects.filter(activite__in=liste_activites).aggregate(Min("date"), Max("date"))
                        liste_periodes = Calcule_periodes_comparatives_generique(parametres, presents, (dates_extremes["date__min"], dates_extremes["date__max"]))
                        if not liste_periodes:
                            data.append(Texte(texte="Impossible de calculer des périodes comparatives (données insuffisantes)."))
                        else:
                            liste_labels, liste_valeurs = [], []
                            for dict_periode in liste_periodes:
                                montant = Prestation.objects.filter(activite__in=liste_activites, date__gte=dict_periode["date_debut"], date__lte=dict_periode["date_fin"]).aggregate(Sum("montant"))["montant__sum"] or 0
                                liste_labels.append(dict_periode["label"])
                                liste_valeurs.append(float(montant))
                            data.append(Histogramme(titre="Evolution du montant des prestations", type_chart="bar", labels=liste_labels, valeurs=liste_valeurs))

                # ================================ ADHESIONS ====================================

                # ---------------------------- ADHESIONS : Nombre -------------------------------

                if rubrique == "adhesions_nombre":
                    data.append(Titre(texte="Nombre d'adhésions"))

                    if parametres["condition"] != "ADHERENTS_PERIODE":
                        data.append(Texte(texte="Donnée accessible uniquement avec la condition 'Adhérents sur une période de dates'."))
                    else:
                        data.append(Texte(texte="%d adhésions enregistrées sur la période sélectionnée." % liste_cotisations.count()))

                        resultats = liste_cotisations.values_list("activites__nom").annotate(nbre=Count("idcotisation", distinct=True)).order_by("-nbre")
                        data.append(Tableau(titre="Répartition des adhésions par activité",
                            colonnes=["Activité", "Nombre d'adhésions"],
                            lignes=[(item[0] if item[0] else "Aucune activité associée", item[1]) for item in resultats]))

                # ---------------------------- ADHESIONS : Type -------------------------------

                if rubrique == "adhesions_type":
                    data.append(Titre(texte="Répartition par type d'adhésion"))

                    if parametres["condition"] != "ADHERENTS_PERIODE":
                        data.append(Texte(texte="Donnée accessible uniquement avec la condition 'Adhérents sur une période de dates'."))
                    else:
                        resultats = liste_cotisations.values_list("type_cotisation__nom").annotate(nbre=Count("idcotisation", distinct=True)).order_by("-nbre")
                        data.append(Tableau(titre="Répartition des adhésions par type",
                            colonnes=["Type d'adhésion", "Nombre d'adhésions"],
                            lignes=[(item[0], item[1]) for item in resultats]))
                        data.append(Camembert(titre="Répartition des adhésions par type",
                            labels=[item[0] for item in resultats],
                            valeurs=[item[1] for item in resultats]))

                # ---------------------------- ADHESIONS : Montant -------------------------------

                if rubrique == "adhesions_montant":
                    data.append(Titre(texte="Montant des adhésions"))

                    if parametres["condition"] != "ADHERENTS_PERIODE":
                        data.append(Texte(texte="Donnée accessible uniquement avec la condition 'Adhérents sur une période de dates'."))
                    else:
                        montant_total = liste_cotisations.aggregate(Sum("prestation__montant"))["prestation__montant__sum"] or 0
                        data.append(Texte(texte="Montant total des adhésions : %.2f €." % montant_total))

                        resultats = liste_cotisations.values_list("type_cotisation__nom").annotate(montant=Sum("prestation__montant")).order_by("-montant")
                        data.append(Tableau(titre="Répartition du montant des adhésions par type",
                            colonnes=["Type d'adhésion", "Montant (€)"],
                            lignes=[(item[0], float(item[1] or 0)) for item in resultats]))
                        data.append(Camembert(titre="Répartition du montant des adhésions par type",
                            labels=[item[0] for item in resultats],
                            valeurs=[float(item[1] or 0) for item in resultats]))

                # ---------------------------- ADHESIONS : Evolution -------------------------------

                if rubrique == "adhesions_evolution":
                    data.append(Titre(texte="Evolution du nombre d'adhésions"))

                    if parametres["condition"] != "ADHERENTS_PERIODE":
                        data.append(Texte(texte="Donnée accessible uniquement avec la condition 'Adhérents sur une période de dates'."))
                    else:
                        # NB : la notion de période comparative (Année/Mois/Vacances) ne s'applique pas à la
                        # condition "Adhérents sur une période de dates" ; on présente donc une évolution par année civile.
                        dates_extremes = Cotisation.objects.filter(type_cotisation__in=parametres["types_cotisations"]).aggregate(Min("date_debut"), Max("date_debut"))
                        date_min, date_max = dates_extremes["date_debut__min"], dates_extremes["date_debut__max"]
                        if not date_min or not date_max:
                            data.append(Texte(texte="Données insuffisantes pour calculer une évolution."))
                        else:
                            liste_labels, liste_valeurs = [], []
                            for annee in range(date_min.year, date_max.year + 1):
                                nbre = Cotisation.objects.filter(type_cotisation__in=parametres["types_cotisations"], date_debut__year=annee).count()
                                liste_labels.append(str(annee))
                                liste_valeurs.append(nbre)
                            data.append(Histogramme(titre="Evolution du nombre d'adhésions par année", type_chart="bar", labels=liste_labels, valeurs=liste_valeurs))

                # ================================ FACTURATION ====================================

                # ---------------------------- FACTURATION : Nombre -------------------------------

                if rubrique == "factures_nombre":
                    data.append(Titre(texte="Nombre et montant des factures"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        factures = Facture.objects.filter(date_edition__range=presents).exclude(etat="annulation")
                        montant_total = factures.aggregate(Sum("total"))["total__sum"] or 0
                        data.append(Texte(texte="%d factures émises, pour un montant total de %.2f €." % (factures.count(), montant_total)))

                # ---------------------------- FACTURATION : Etat -------------------------------

                if rubrique == "factures_etat":
                    data.append(Titre(texte="Répartition des factures par état"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        factures = Facture.objects.filter(date_edition__range=presents)
                        nbre_annulees = factures.filter(etat="annulation").count()
                        nbre_validees = factures.count() - nbre_annulees
                        data.append(Tableau(titre="Répartition des factures par état",
                            colonnes=["Etat", "Nombre de factures"],
                            lignes=[("Validées", nbre_validees), ("Annulées", nbre_annulees)]))
                        data.append(Camembert(titre="Répartition des factures par état",
                            labels=["Validées", "Annulées"],
                            valeurs=[nbre_validees, nbre_annulees],
                            couleurs=["rgba(75, 192, 100, 0.5)", "rgba(255, 99, 132, 0.5)"]))

                # ---------------------------- FACTURATION : Impayés -------------------------------

                if rubrique == "factures_impayes":
                    data.append(Titre(texte="Impayés"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        factures_impayees = Facture.objects.filter(date_edition__range=presents, solde_actuel__gt=0).exclude(etat="annulation")
                        montant_impaye = factures_impayees.aggregate(Sum("solde_actuel"))["solde_actuel__sum"] or 0
                        data.append(Texte(texte="%d factures avec un solde impayé, pour un montant total de %.2f €." % (factures_impayees.count(), montant_impaye)))

                        tranches = [(0, 50), (50, 100), (100, 300), (300, None)]
                        lignes = []
                        for tranche_min, tranche_max in tranches:
                            if tranche_max:
                                nbre = factures_impayees.filter(solde_actuel__gte=tranche_min, solde_actuel__lt=tranche_max).count()
                                label = "%d € - %d €" % (tranche_min, tranche_max)
                            else:
                                nbre = factures_impayees.filter(solde_actuel__gte=tranche_min).count()
                                label = "Plus de %d €" % tranche_min
                            lignes.append((label, nbre))
                        data.append(Tableau(titre="Répartition des impayés par tranche de montant",
                            colonnes=["Tranche de montant", "Nombre de factures"],
                            lignes=lignes))
                        data.append(Camembert(titre="Répartition des impayés par tranche de montant",
                            labels=[l[0] for l in lignes],
                            valeurs=[l[1] for l in lignes]))

                # ---------------------------- FACTURATION : Evolution -------------------------------

                if rubrique == "factures_evolution":
                    data.append(Titre(texte="Evolution du montant facturé"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        dates_extremes = Facture.objects.exclude(etat="annulation").aggregate(Min("date_edition"), Max("date_edition"))
                        liste_periodes = Calcule_periodes_comparatives_generique(parametres, presents, (dates_extremes["date_edition__min"], dates_extremes["date_edition__max"]))
                        if not liste_periodes:
                            data.append(Texte(texte="Impossible de calculer des périodes comparatives (données insuffisantes)."))
                        else:
                            liste_labels, liste_valeurs = [], []
                            for dict_periode in liste_periodes:
                                montant = Facture.objects.exclude(etat="annulation").filter(date_edition__gte=dict_periode["date_debut"], date_edition__lte=dict_periode["date_fin"]).aggregate(Sum("total"))["total__sum"] or 0
                                liste_labels.append(dict_periode["label"])
                                liste_valeurs.append(float(montant))
                            data.append(Histogramme(titre="Evolution du montant facturé", type_chart="bar", labels=liste_labels, valeurs=liste_valeurs))

                # ================================ REGLEMENTS ====================================

                # ---------------------------- REGLEMENTS : Nombre -------------------------------

                if rubrique == "reglements_nombre":
                    data.append(Titre(texte="Nombre et montant des règlements"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        reglements = Reglement.objects.filter(date__range=presents)
                        montant_total = reglements.aggregate(Sum("montant"))["montant__sum"] or 0
                        data.append(Texte(texte="%d règlements enregistrés, pour un montant total encaissé de %.2f €." % (reglements.count(), montant_total)))

                # ---------------------------- REGLEMENTS : Mode -------------------------------

                if rubrique == "reglements_mode":
                    data.append(Titre(texte="Répartition par mode de règlement"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        resultats = Reglement.objects.filter(date__range=presents).values_list("mode__label").annotate(nbre=Count("idreglement"), montant=Sum("montant")).order_by("-montant")
                        data.append(Tableau(titre="Répartition du montant encaissé par mode de règlement",
                            colonnes=["Mode de règlement", "Nombre", "Montant (€)"],
                            lignes=[(item[0], item[1], float(item[2] or 0)) for item in resultats]))
                        data.append(Camembert(titre="Répartition du montant encaissé par mode de règlement",
                            labels=[item[0] for item in resultats],
                            valeurs=[float(item[2] or 0) for item in resultats]))

                # ---------------------------- REGLEMENTS : Evolution -------------------------------

                if rubrique == "reglements_evolution":
                    data.append(Titre(texte="Evolution du montant encaissé"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        dates_extremes = Reglement.objects.aggregate(Min("date"), Max("date"))
                        liste_periodes = Calcule_periodes_comparatives_generique(parametres, presents, (dates_extremes["date__min"], dates_extremes["date__max"]))
                        if not liste_periodes:
                            data.append(Texte(texte="Impossible de calculer des périodes comparatives (données insuffisantes)."))
                        else:
                            liste_labels, liste_valeurs = [], []
                            for dict_periode in liste_periodes:
                                montant = Reglement.objects.filter(date__gte=dict_periode["date_debut"], date__lte=dict_periode["date_fin"]).aggregate(Sum("montant"))["montant__sum"] or 0
                                liste_labels.append(dict_periode["label"])
                                liste_valeurs.append(float(montant))
                            data.append(Histogramme(titre="Evolution du montant encaissé", type_chart="bar", labels=liste_labels, valeurs=liste_valeurs))

                # ================================ RAPPELS ====================================

                # ---------------------------- RAPPELS : Nombre -------------------------------

                if rubrique == "rappels_nombre":
                    data.append(Titre(texte="Nombre et montant des rappels"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        rappels = Rappel.objects.filter(date_edition__range=presents)
                        montant_total = rappels.aggregate(Sum("solde"))["solde__sum"] or 0
                        data.append(Texte(texte="%d rappels envoyés, pour un solde rappelé total de %.2f €." % (rappels.count(), montant_total)))

                        resultats = rappels.values_list("modele__label").annotate(nbre=Count("idrappel")).order_by("-nbre")
                        data.append(Tableau(titre="Répartition des rappels par modèle",
                            colonnes=["Modèle de rappel", "Nombre de rappels"],
                            lignes=[(item[0], item[1]) for item in resultats]))

                # ================================ APPLICATION ====================================

                # ---------------------------- APPLICATION : Actions -------------------------------

                if rubrique == "application_actions":
                    data.append(Titre(texte="Actions les plus fréquentes dans le logiciel"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        resultats = Historique.objects.filter(horodatage__date__range=presents).values_list("titre").annotate(nbre=Count("idaction")).order_by("-nbre")[:20]
                        data.append(Tableau(titre="Top 20 des actions les plus fréquentes",
                            colonnes=["Action", "Nombre d'occurrences"],
                            lignes=[(item[0], item[1]) for item in resultats]))

                # ---------------------------- APPLICATION : Connexions au portail -------------------------------

                if rubrique == "application_connexions":
                    data.append(Titre(texte="Connexions au portail famille"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        connexions = Historique.objects.filter(portail=True, titre="Connexion au portail", horodatage__date__range=presents)
                        data.append(Texte(texte="%d connexions au portail famille sur la période sélectionnée." % connexions.count()))

                        resultats = connexions.values_list("horodatage__date").annotate(nbre=Count("idaction")).order_by("horodatage__date")
                        data.append(Histogramme(titre="Nombre de connexions au portail par jour", type_chart="line", chronologie="date",
                            labels=[str(item[0]) for item in resultats],
                            valeurs=[item[1] for item in resultats]))

                # ================================ PORTAIL ====================================

                # ---------------------------- PORTAIL : Réservations -------------------------------

                if rubrique == "portail_reservations":
                    data.append(Titre(texte="Réservations effectuées depuis le portail famille"))

                    if not condition_dates_prestations:
                        data.append(Texte(texte="Donnée accessible uniquement avec une condition de type période de dates (Année, Mois, Vacances ou Période)."))
                    else:
                        condition = Q(titre="Ajout d'une consommation") & Q(portail=True, activite__in=liste_activites, horodatage__date__range=presents)
                        reservations = Historique.objects.filter(condition)
                        data.append(Texte(texte="%d réservations effectuées depuis le portail famille sur la période sélectionnée." % reservations.count()))

                        resultats = reservations.values_list("activite__nom").annotate(nbre=Count("idaction")).order_by("-nbre")
                        data.append(Tableau(titre="Répartition des réservations portail par activité",
                            colonnes=["Activité", "Nombre de réservations"],
                            lignes=[(item[0] if item[0] else "Activité non renseignée", item[1]) for item in resultats]))
                        data.append(Camembert(titre="Répartition des réservations portail par activité",
                            labels=[item[0] if item[0] else "Activité non renseignée" for item in resultats],
                            valeurs=[item[1] for item in resultats]))

                data.append(Espace(hauteur=50))

        return data
