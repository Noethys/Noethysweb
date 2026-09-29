# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Export du paramétrage d'une activité au format JSON, en vue d'une analyse par une IA.
Utilisé par la page Paramétrage > Activités > Contrôle IA du paramétrage
et par la commande "manage.py export_parametrage_activite".

Aucune donnée personnelle des familles n'est exportée : seuls le paramétrage de l'activité,
le calendrier (vacances, jours fériés) et des statistiques agrégées sont inclus.
"""

import json, datetime, decimal
from collections import Counter, defaultdict
from django.db.models import Count, Q
from django.db.models.fields.files import FileField
from core.models import Activite, ResponsableActivite, Agrement, Groupe, Unite, UniteRemplissage, CategorieEvenement, \
                        Evenement, CategorieTarif, NomTarif, Tarif, TarifLigne, CombiTarif, ModelePrestation, Ouverture, \
                        Remplissage, PortailPeriode, TypeCotisation, Vacance, Ferie, Inscription, Consommation

FORMAT_EXPORT = "noethysweb-parametrage-activite/1"
JOURS_SEMAINE = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

# Champs jamais exportés (fichiers, champs techniques sans intérêt pour l'analyse)
CHAMPS_EXCLUS = {"logo", "image"}

# Jours fériés fixes légaux en France : contrôlés même s'ils n'ont pas été saisis dans Noethysweb
FERIES_FIXES_FRANCE = [(1, 1, "Jour de l'an"), (1, 5, "Fête du travail"), (8, 5, "Victoire 1945"), (14, 7, "Fête nationale"),
                       (15, 8, "Assomption"), (1, 11, "Toussaint"), (11, 11, "Armistice 1918"), (25, 12, "Noël")]


def Encodeur(valeur):
    """ Conversion des types non sérialisables en JSON """
    if isinstance(valeur, (datetime.date, datetime.datetime, datetime.time)):
        return valeur.isoformat()
    if isinstance(valeur, decimal.Decimal):
        return str(valeur)
    if isinstance(valeur, (set, frozenset)):
        return sorted(valeur)
    return str(valeur)


def Libelle(obj):
    try:
        return str(obj)
    except Exception:
        return None


def Serialiser(obj, exclure=()):
    """ Sérialise un objet de modèle de façon générique (champs, FK, M2M) """
    resultat = {"id": obj.pk}
    for champ in obj._meta.concrete_fields:
        if champ.primary_key or champ.name in exclure or champ.name in CHAMPS_EXCLUS or isinstance(champ, FileField):
            continue
        if champ.is_relation:
            id_lie = getattr(obj, champ.attname)
            if id_lie is None:
                continue
            resultat[champ.name] = {"id": id_lie, "libelle": Libelle(getattr(obj, champ.name))}
            continue
        valeur = getattr(obj, champ.attname)
        if valeur is None or valeur == "" or (isinstance(valeur, (list, tuple)) and not valeur):
            continue
        resultat[champ.name] = valeur
        if champ.choices:
            resultat[champ.name + "_libelle"] = str(getattr(obj, "get_%s_display" % champ.name)())
    for champ in obj._meta.many_to_many:
        if champ.name in exclure:
            continue
        valeurs = [{"id": o.pk, "libelle": Libelle(o)} for o in getattr(obj, champ.name).all()]
        if valeurs:
            resultat[champ.name] = valeurs
    return resultat


def Dictionnaire_champs(modeles):
    """ Libellés et aides des champs, pour que l'analyse comprenne le sens de chaque champ """
    dictionnaire = {}
    for modele in modeles:
        champs = {}
        for champ in list(modele._meta.concrete_fields) + list(modele._meta.many_to_many):
            if champ.primary_key or champ.name in CHAMPS_EXCLUS or isinstance(champ, FileField):
                continue
            texte = str(champ.verbose_name)
            if getattr(champ, "help_text", None):
                texte += " — " + str(champ.help_text)
            champs[champ.name] = texte
        dictionnaire[modele.__name__] = {"libelle": str(modele._meta.verbose_name), "champs": champs}
    return dictionnaire


def Plages(dates):
    """ Compresse une liste de dates en plages consécutives """
    plages, debut, precedente = [], None, None
    for date in sorted(dates):
        if debut is None:
            debut = precedente = date
        elif date - precedente == datetime.timedelta(days=1):
            precedente = date
        else:
            plages.append(debut.isoformat() if debut == precedente else "%s → %s" % (debut, precedente))
            debut = precedente = date
    if debut is not None:
        plages.append(debut.isoformat() if debut == precedente else "%s → %s" % (debut, precedente))
    return plages



def Get_periode(activite, depuis=None, jusqua=None):
    """ Période analysée : paramètres, sinon dates de l'activité, sinon ±1 an autour d'aujourd'hui """
    depuis_option, jusqua_option = depuis, jusqua
    aujourdhui = datetime.date.today()
    if activite.date_fin and activite.date_debut:
        depuis, jusqua = activite.date_debut, activite.date_fin
    else:
        depuis = max(activite.date_debut, aujourdhui - datetime.timedelta(days=365)) if activite.date_debut else aujourdhui - datetime.timedelta(days=365)
        jusqua = aujourdhui + datetime.timedelta(days=365)
    return depuis_option or depuis, jusqua_option or jusqua

def Exporter_activite(activite, depuis=None, jusqua=None, tous_les_tarifs=False, noms_responsables=False):
    """ Renvoie un dict (à sérialiser avec Encodeur) du paramétrage de l'activité """
    depuis, jusqua = Get_periode(activite, depuis, jusqua)
    if depuis > jusqua:
        raise ValueError("La date de début de la période analysée est postérieure à la date de fin")

    # Calendrier
    vacances = Vacance.objects.filter(date_fin__gte=depuis, date_debut__lte=jusqua).order_by("date_debut")
    liste_vacances = [{"nom": v.nom, "annee": v.annee, "date_debut": v.date_debut, "date_fin": v.date_fin} for v in vacances]
    annees = range(depuis.year, jusqua.year + 1)
    feries = Ferie.objects.filter(Q(type="fixe") | Q(type="variable", annee__in=annees)).order_by("type", "annee", "mois", "jour")
    liste_feries = [{"nom": f.nom, "type": f.type, "jour": f.jour, "mois": f.mois, "annee": f.annee or None} for f in feries]

    dates_feries = {}
    for annee in annees:
        for jour, mois, nom in FERIES_FIXES_FRANCE:
            dates_feries[datetime.date(annee, mois, jour)] = nom
        for f in feries:
            if f.type == "fixe" or f.annee == annee:
                try:
                    dates_feries[datetime.date(annee, f.mois, f.jour)] = f.nom
                except ValueError:
                    pass
    feries_fixes_saisis = {(f.jour, f.mois) for f in feries if f.type == "fixe"}
    feries_fixes_non_saisis = [nom for jour, mois, nom in FERIES_FIXES_FRANCE if (jour, mois) not in feries_fixes_saisis]

    def Periode_calendrier(date):
        for v in vacances:
            if v.date_debut <= date <= v.date_fin:
                return "Vacances %s %s" % (v.nom, v.annee)
        return "Hors vacances"

    def Resume_dates(dates):
        return {
            "nbre_dates": len(dates),
            "premiere_date": min(dates),
            "derniere_date": max(dates),
            "jours_semaine": dict(Counter(JOURS_SEMAINE[d.weekday()] for d in sorted(dates))),
            "repartition_calendrier": dict(Counter(Periode_calendrier(d) for d in sorted(dates))),
            "dates_jours_feries": [{"date": d, "nom": dates_feries[d]} for d in sorted(dates) if d in dates_feries],
            "plages": Plages(dates),
        }

    # Responsables (anonymisés par défaut)
    responsables = []
    for index, responsable in enumerate(ResponsableActivite.objects.filter(activite=activite).order_by("pk"), 1):
        dict_responsable = Serialiser(responsable, exclure=("activite",))
        if not noms_responsables:
            dict_responsable["nom"] = "Responsable %d" % index
        responsables.append(dict_responsable)

    # Tarifs
    tarifs = Tarif.objects.filter(activite=activite).select_related("nom_tarif").order_by("date_debut", "pk")
    if not tous_les_tarifs:
        tarifs = tarifs.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=depuis))
    liste_tarifs = []
    for tarif in tarifs:
        dict_tarif = Serialiser(tarif, exclure=("activite",))
        dict_tarif["lignes"] = [Serialiser(ligne, exclure=("activite", "tarif")) for ligne in TarifLigne.objects.filter(tarif=tarif).order_by("num_ligne", "pk")]
        dict_tarif["combinaisons_unites"] = [Serialiser(combi, exclure=("tarif",)) for combi in CombiTarif.objects.filter(tarif=tarif).order_by("pk")]
        liste_tarifs.append(dict_tarif)

    # Ouvertures (résumées par unité et groupe)
    dates_ouvertures = defaultdict(list)
    for unite_id, groupe_id, date in Ouverture.objects.filter(activite=activite, date__range=(depuis, jusqua)).values_list("unite_id", "groupe_id", "date"):
        dates_ouvertures[(unite_id, groupe_id)].append(date)
    unites = {u.pk: u.nom for u in Unite.objects.filter(activite=activite)}
    groupes = {g.pk: g.nom for g in Groupe.objects.filter(activite=activite)}
    liste_ouvertures = []
    for (unite_id, groupe_id), dates in sorted(dates_ouvertures.items()):
        liste_ouvertures.append({"unite": {"id": unite_id, "libelle": unites.get(unite_id)}, "groupe": {"id": groupe_id, "libelle": groupes.get(groupe_id)}, **Resume_dates(dates)})

    # Remplissage (capacités résumées par unité de remplissage et groupe)
    remplissages = defaultdict(list)
    for unite_id, groupe_id, date, places in Remplissage.objects.filter(activite=activite, date__range=(depuis, jusqua)).values_list("unite_remplissage_id", "groupe_id", "date", "places"):
        remplissages[(unite_id, groupe_id)].append((date, places))
    unites_remplissage = {u.pk: u.nom for u in UniteRemplissage.objects.filter(activite=activite)}
    liste_remplissage = []
    for (unite_id, groupe_id), valeurs in sorted(remplissages.items(), key=lambda x: (x[0][0], x[0][1] or 0)):
        dates = [d for d, p in valeurs]
        liste_remplissage.append({
            "unite_remplissage": {"id": unite_id, "libelle": unites_remplissage.get(unite_id)},
            "groupe": {"id": groupe_id, "libelle": groupes.get(groupe_id)} if groupe_id else None,
            "nbre_dates": len(dates), "premiere_date": min(dates), "derniere_date": max(dates),
            "places": {str(p): n for p, n in Counter(p for d, p in valeurs).most_common()},
        })

    # Statistiques agrégées (aucune donnée nominative)
    inscriptions = Inscription.objects.filter(activite=activite)
    inscriptions_periode = inscriptions.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=depuis), date_debut__lte=jusqua)
    consommations = Consommation.objects.filter(activite=activite, date__range=(depuis, jusqua))
    statistiques = {
        "inscriptions_total": inscriptions.count(),
        "inscriptions_periode_par_statut": {str(l["statut"]): l["nbre"] for l in inscriptions_periode.values("statut").annotate(nbre=Count("pk"))},
        "inscriptions_periode_par_groupe": {groupes.get(l["groupe"], l["groupe"]): l["nbre"] for l in inscriptions_periode.values("groupe").annotate(nbre=Count("pk"))},
        "inscriptions_periode_par_categorie_tarif": {l["categorie_tarif__nom"]: l["nbre"] for l in inscriptions_periode.values("categorie_tarif__nom").annotate(nbre=Count("pk"))},
        "consommations_periode_par_unite": {unites.get(l["unite"], l["unite"]): l["nbre"] for l in consommations.values("unite").annotate(nbre=Count("pk"))},
        "consommations_periode_par_etat": {str(l["etat"]): l["nbre"] for l in consommations.values("etat").annotate(nbre=Count("pk"))},
    }

    return {
        "meta": {
            "format": FORMAT_EXPORT,
            "version_noethysweb": Get_version(),
            "date_export": datetime.datetime.now().replace(microsecond=0),
            "periode_analysee": {"depuis": depuis, "jusqua": jusqua},
            "remarques": [
                "Aucune donnée personnelle des familles n'est incluse : seules des statistiques agrégées.",
                "Les ouvertures, remplissages et événements sont limités à la période analysée.",
                "Les tarifs terminés avant la période analysée sont exclus%s." % (" (option --tous-les-tarifs active : ils sont inclus)" if tous_les_tarifs else ""),
                "Les dates d'ouverture sont résumées par unité et groupe (plages de dates consécutives).",
                "Les jours fériés fixes légaux français sont contrôlés dans les ouvertures même s'ils ne sont pas saisis dans Noethysweb (voir calendrier.feries_fixes_legaux_non_saisis).",
            ],
        },
        "dictionnaire_champs": Dictionnaire_champs([Activite, ResponsableActivite, Agrement, Groupe, Unite, UniteRemplissage, CategorieEvenement,
                                                    Evenement, CategorieTarif, NomTarif, Tarif, TarifLigne, CombiTarif, ModelePrestation,
                                                    PortailPeriode, TypeCotisation]),
        "activite": Serialiser(activite),
        "responsables": responsables,
        "agrements": [Serialiser(o, exclure=("activite",)) for o in Agrement.objects.filter(activite=activite).order_by("date_debut")],
        "groupes": [Serialiser(o, exclure=("activite",)) for o in Groupe.objects.filter(activite=activite).order_by("ordre", "pk")],
        "unites": [Serialiser(o, exclure=("activite",)) for o in Unite.objects.filter(activite=activite).order_by("ordre", "pk")],
        "unites_remplissage": [Serialiser(o, exclure=("activite",)) for o in UniteRemplissage.objects.filter(activite=activite).order_by("ordre", "pk")],
        "categories_tarifs": [Serialiser(o, exclure=("activite",)) for o in CategorieTarif.objects.filter(activite=activite).order_by("nom")],
        "noms_tarifs": [Serialiser(o, exclure=("activite",)) for o in NomTarif.objects.filter(activite=activite).order_by("nom")],
        "tarifs": liste_tarifs,
        "modeles_prestations": [Serialiser(o, exclure=("activite",)) for o in ModelePrestation.objects.filter(activite=activite).order_by("pk")],
        "types_cotisations_associes": [Serialiser(o, exclure=("activite",)) for o in TypeCotisation.objects.filter(activite=activite).order_by("nom")],
        "categories_evenements": [Serialiser(o, exclure=("activite",)) for o in CategorieEvenement.objects.filter(activite=activite).order_by("nom")],
        "evenements": [Serialiser(o, exclure=("activite",)) for o in Evenement.objects.filter(activite=activite, date__range=(depuis, jusqua)).order_by("date", "pk")],
        "periodes_portail": [Serialiser(o, exclure=("activite",)) for o in PortailPeriode.objects.filter(activite=activite, date_fin__gte=depuis, date_debut__lte=jusqua).order_by("date_debut")],
        "ouvertures": liste_ouvertures,
        "remplissage": liste_remplissage,
        "statistiques": statistiques,
        "calendrier": {"vacances": liste_vacances, "feries": liste_feries, "feries_fixes_legaux_non_saisis": feries_fixes_non_saisis},
    }


PROMPT = """Tu es expert du logiciel Noethysweb. Le fichier JSON joint contient l'export du paramétrage d'une activité. \
La rubrique "dictionnaire_champs" donne le sens de chaque champ et la rubrique "meta" précise la période analysée. \
Analyse la cohérence de ce paramétrage : unités de consommation, groupes, catégories et noms de tarifs, tarifs (montants, \
lignes, combinaisons d'unités, états facturés, filtres par catégorie, groupe ou caisse), ouvertures (par rapport \
aux vacances, aux jours fériés et aux week-ends), remplissage (capacités), agréments, paramètres et périodes du portail. \
Présente les anomalies ou risques dans un tableau par ordre de gravité (critique, important, à vérifier) avec les colonnes : \
gravité / élément concerné / problème / correction proposée dans Noethysweb. Distingue ce qui concerne le passé \
de ce qui reste à venir. N'invente pas de fonctionnalité : si tu n'es pas sûr du sens d'un champ, signale-le comme point à vérifier."""


def Get_version():
    try:
        from noethysweb.version import GetVersion
        return GetVersion()
    except Exception:
        return None


def Get_json(activite, **kwargs):
    """ Renvoie l'export sous forme de texte JSON """
    return json.dumps(Exporter_activite(activite, **kwargs), ensure_ascii=False, indent=1, default=Encodeur)


def Get_nom_fichier(activite):
    return "parametrage_activite_%d_%s.json" % (activite.pk, datetime.date.today().isoformat())
