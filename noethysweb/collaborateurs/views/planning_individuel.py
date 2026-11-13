# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json, decimal, secrets, calendar
logger = logging.getLogger(__name__)
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.db import transaction
from django.db.models import Q
from core.views.base import CustomView
from core.models import Collaborateur, TypeEvenementCollaborateur, ModelePlanningCollaborateur, ContratCollaborateur, AjustementObjectifCollaborateur
from core.utils import utils_parametres, utils_historique
from collaborateurs.utils import utils_planning, utils_objectif
from collaborateurs.utils.utils_planning import Parse_date
from collaborateurs.utils.utils_affectations import Arbre
from collaborateurs.views.collaborateur import Onglet

PERMISSION = "core.planning_individuel"
CATEGORIE_PREFERENCES = "planning_individuel"
PREFERENCES_DEFAUT = {"vue": "calendrier", "journee_debut": "09:00", "journee_fin": "17:00", "matin_debut": "08:30", "matin_fin": "12:00",
                      "am_debut": "13:30", "am_fin": "17:00", "ignorer_non_ouvres": True}
VUES = ("calendrier", "colonnes", "mois")


def Peut_acceder(user=None):
    return user.has_perm(PERMISSION) or user.has_perm(utils_planning.PERMISSION)


def Verifie_permission(function):
    def _function(request, *args, **kwargs):
        if not Peut_acceder(request.user):
            return HttpResponseForbidden()
        return function(request, *args, **kwargs)
    return _function


def Collaborateurs_accessibles(user=None):
    """ Collaborateurs visibles par l'utilisateur (mêmes règles que la liste des collaborateurs) """
    conditions = Q(groupes__superviseurs=user) | Q(groupes__superviseurs__isnull=True)
    return Collaborateur.objects.filter(conditions).distinct().order_by("nom", "prenom")


def Get_collaborateur(request, modifiable=False):
    """ Renvoie le collaborateur demandé s'il est accessible (et modifiable si demandé) """
    try:
        idcollaborateur = int(request.POST.get("idcollaborateur", 0))
    except (TypeError, ValueError):
        return None
    collaborateur = Collaborateurs_accessibles(request.user).filter(pk=idcollaborateur).first()
    if collaborateur and modifiable and collaborateur.pk not in utils_planning.Get_ids_modifiables(request.user):
        return None
    return collaborateur


def Get_periode_demandee(request, idcollaborateur=None, parametres=None):
    type_periode = request.POST.get("type_periode") or utils_objectif.Type_periode_defaut(idcollaborateur, parametres)
    if type_periode not in ("CIVILE", "SCOLAIRE"):
        type_periode = "CIVILE"
    try:
        annee = int(request.POST.get("annee") or 0)
    except ValueError:
        annee = 0
    if not 1900 < annee < 2200:
        annee = utils_objectif.Annee_periode(datetime.date.today(), type_periode, parametres)
    return utils_objectif.Get_periode(annee, type_periode, parametres)


def Get_preferences(user=None):
    preferences = dict(PREFERENCES_DEFAUT)
    stockees = utils_parametres.Get(nom="preferences", categorie=CATEGORIE_PREFERENCES, utilisateur=user, valeur={}) or {}
    for nom, defaut in PREFERENCES_DEFAUT.items():
        valeur = stockees.get(nom)
        if valeur is None:
            continue
        if nom == "vue" and valeur not in VUES:
            continue
        if isinstance(defaut, bool):
            valeur = bool(valeur)
        elif nom != "vue":
            try:
                datetime.datetime.strptime(str(valeur), "%H:%M")
            except ValueError:
                continue
        preferences[nom] = valeur
    return preferences


def Calcul(collaborateur=None, periode=None, parametres=None):
    return utils_objectif.Calcul_objectif(idcollaborateur=collaborateur.pk, periode=periode, parametres=parametres)


# ------------------------------------------------- Données -------------------------------------------------

@Verifie_permission
def Get_donnees(request):
    collaborateur = Get_collaborateur(request)
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    parametres = utils_objectif.Get_parametres()
    periode = Get_periode_demandee(request, collaborateur.pk, parametres)
    calcul = Calcul(collaborateur, periode, parametres)

    contrats = [{"d": str(contrat.date_debut), "f": str(contrat.date_fin) if contrat.date_fin else None, "h": float(contrat.heures_hebdo) if contrat.heures_hebdo else None,
                 "poste": contrat.type_poste.nom, "mode": contrat.get_objectif_mode_display()}
                for contrat in ContratCollaborateur.objects.select_related("type_poste").filter(collaborateur=collaborateur).order_by("date_debut")]

    evenements = [utils_planning.Serialiser_evenement(evenement) for evenement in utils_planning.Get_evenements(periode["debut"], periode["fin"], [collaborateur.pk])]
    resultat = {
        "collaborateur": {"id": collaborateur.pk, "nom": collaborateur.nom, "prenom": collaborateur.prenom or "", "contrats": contrats,
                          "modifiable": collaborateur.pk in utils_planning.Get_ids_modifiables(request.user),
                          "mail": collaborateur.travail_mail or collaborateur.mail or "", "mail_pro": bool(collaborateur.travail_mail)},
        "categories": [{"id": categorie.pk, "nom": categorie.nom, "couleur": categorie.couleur, "type": categorie.type, "chevauchement": categorie.chevauchement_possible,
                        "objectif": categorie.temps_travail_objectif} for categorie in TypeEvenementCollaborateur.objects.all().order_by("nom")],
        "affectations": Arbre().Get_liste_dict(),
        "modeles": [{"id": modele.pk, "nom": modele.nom} for modele in ModelePlanningCollaborateur.objects.all().order_by("nom")],
        "evenements": evenements,
        "objectif": calcul.Get_dict(),
        "periode_suivante": utils_objectif.Periode_suivante(periode, parametres)["libelle"],
        "parametres": parametres,
        "peut_regler_tous": utils_planning.Peut_regler_pour_tous(request.user),
        "preferences": Get_preferences(request.user),
        "aujourdhui": str(datetime.date.today()),
    }
    resultat.update(utils_planning.Get_dates_speciales(periode["debut"], periode["fin"]))
    return JsonResponse(resultat)


@Verifie_permission
def Get_objectif(request):
    collaborateur = Get_collaborateur(request)
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    parametres = utils_objectif.Get_parametres()
    periode = Get_periode_demandee(request, collaborateur.pk, parametres)
    return JsonResponse({"objectif": Calcul(collaborateur, periode, parametres).Get_dict()})


@Verifie_permission
def Memoriser_preferences(request):
    try:
        preferences = json.loads(request.POST.get("preferences", "{}"))
    except ValueError:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    actuelles = Get_preferences(request.user)
    actuelles.update({nom: valeur for nom, valeur in preferences.items() if nom in PREFERENCES_DEFAUT})
    utils_parametres.Set(nom="preferences", categorie=CATEGORIE_PREFERENCES, utilisateur=request.user, valeur=actuelles)
    return JsonResponse({"preferences": Get_preferences(request.user)})


@Verifie_permission
def Enregistrer_parametres(request):
    if not utils_planning.Peut_regler_pour_tous(request.user):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier les paramètres généraux"}, status=403)
    try:
        parametres = json.loads(request.POST.get("parametres", "{}"))
    except ValueError:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    return JsonResponse({"parametres": utils_objectif.Set_parametres(parametres)})


# ------------------------------------------------- Enregistrement des évènements -------------------------------------------------

@Verifie_permission
def Enregistrer(request):
    """ Enregistre un lot d'opérations limitées au collaborateur affiché """
    collaborateur = Get_collaborateur(request, modifiable=True)
    if not collaborateur:
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier le planning de ce collaborateur"}, status=403)
    try:
        operations = json.loads(request.POST.get("operations", "[]"))
    except ValueError:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    if not operations:
        return JsonResponse({"crees": {}, "maj": {}, "supprimes": []})

    # Toutes les opérations doivent concerner le collaborateur affiché
    from core.models import EvenementCollaborateur
    ids = [int(operation["id"]) for operation in operations if operation.get("op") in ("update", "delete")]
    if EvenementCollaborateur.objects.filter(pk__in=ids).exclude(collaborateur=collaborateur).exists():
        return JsonResponse({"erreur": "Opération non autorisée"}, status=403)
    for operation in operations:
        if operation.get("op") in ("create", "update") and str(operation.get("data", {}).get("c")) != str(collaborateur.pk):
            return JsonResponse({"erreur": "Opération non autorisée"}, status=403)

    try:
        with transaction.atomic():
            resultat = utils_planning.Enregistrer_operations(operations=operations, user=request.user)
            if "conflits" in resultat:
                transaction.set_rollback(True)
    except utils_planning.Erreur_enregistrement as erreur:
        return JsonResponse({"erreur": str(erreur)}, status=409)

    if "conflits" in resultat:
        return JsonResponse({"erreur": "Le planning a été modifié par un autre utilisateur entre-temps. L'affichage a été actualisé, recommencez votre modification.",
                             "conflits": resultat["conflits"]}, status=409)
    return JsonResponse(resultat)


@Verifie_permission
def Appliquer_modele(request):
    collaborateur = Get_collaborateur(request, modifiable=True)
    if not collaborateur:
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier le planning de ce collaborateur"}, status=403)
    try:
        modeles = [int(valeur) for valeur in json.loads(request.POST.get("modeles", "[]"))]
        dates = sorted(set(Parse_date(valeur) for valeur in json.loads(request.POST.get("dates", "[]"))))
    except (TypeError, ValueError):
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    if not modeles or not dates:
        return JsonResponse({"erreur": "Sélectionnez au moins un modèle et une date"}, status=400)
    if len(dates) > 400:
        return JsonResponse({"erreur": "La période est trop longue"}, status=400)
    apercu = request.POST.get("apercu") == "true"
    conflit = request.POST.get("conflit", "ignorer")
    if conflit not in ("ignorer", "remplacer", "effacer"):
        conflit = "ignorer"
    nouveaux, hors_contrat = utils_planning.Generer_depuis_modeles(modeles=modeles, collaborateurs=[collaborateur.pk], dates=dates)
    with transaction.atomic():
        resultat = utils_planning.Creer_par_lot(nouveaux=nouveaux, collaborateurs=[collaborateur.pk], dates=dates, conflit=conflit, apercu=apercu,
                                                user=request.user, libelle="modèle de planning")
    resultat["nbre_hors_contrat"] = hors_contrat
    return JsonResponse(resultat)


# ------------------------------------------------- Ajustements et reports -------------------------------------------------

def Texte_ajustement(ajustement=None):
    return "%s : %s (%s)" % (ajustement.date.strftime("%d/%m/%Y"), utils_objectif.Format_nombre(float(ajustement.valeur)), ajustement.motif or ajustement.get_type_display())


@Verifie_permission
def Enregistrer_ajustement(request):
    collaborateur = Get_collaborateur(request, modifiable=True)
    if not collaborateur:
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier ce collaborateur"}, status=403)
    date = Parse_date(request.POST.get("date"))
    try:
        valeur = decimal.Decimal(str(request.POST.get("valeur", "")).replace(",", ".").strip())
    except decimal.InvalidOperation:
        valeur = None
    if not date:
        return JsonResponse({"erreur": "Saisissez une date d'effet"}, status=400)
    if valeur is None or not valeur.is_finite() or abs(valeur) >= 100000:
        return JsonResponse({"erreur": "Saisissez une valeur correcte"}, status=400)
    if valeur == 0:
        return JsonResponse({"erreur": "La valeur ne peut pas être nulle"}, status=400)
    motif = (request.POST.get("motif") or "").strip()[:300]

    idajustement = int(request.POST.get("idajustement") or 0)
    if idajustement:
        ajustement = AjustementObjectifCollaborateur.objects.filter(pk=idajustement, collaborateur=collaborateur).first()
        if not ajustement:
            return JsonResponse({"erreur": "Cet ajustement n'existe plus"}, status=404)
        ancien = Texte_ajustement(ajustement)
        titre = "Modification d'un ajustement d'objectif"
    else:
        ajustement = AjustementObjectifCollaborateur(collaborateur=collaborateur, type="AJUSTEMENT")
        ancien, titre = None, "Ajout d'un ajustement d'objectif"
    ajustement.date, ajustement.valeur, ajustement.motif, ajustement.utilisateur = date, valeur.quantize(decimal.Decimal("0.01")), motif or None, request.user
    ajustement.save()
    utils_historique.Ajouter(titre=titre, detail=Texte_ajustement(ajustement), old=ancien, utilisateur=request.user, collaborateur=collaborateur.pk,
                             objet="Ajustement d'objectif", idobjet=ajustement.pk, classe="AjustementObjectifCollaborateur")
    return Get_objectif(request)


@Verifie_permission
def Supprimer_ajustement(request):
    collaborateur = Get_collaborateur(request, modifiable=True)
    if not collaborateur:
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier ce collaborateur"}, status=403)
    ajustement = AjustementObjectifCollaborateur.objects.filter(pk=int(request.POST.get("idajustement") or 0), collaborateur=collaborateur).first()
    if not ajustement:
        return JsonResponse({"erreur": "Cet ajustement n'existe plus"}, status=404)
    utils_historique.Ajouter(titre="Suppression d'un ajustement d'objectif", detail=Texte_ajustement(ajustement), utilisateur=request.user, collaborateur=collaborateur.pk,
                             objet="Ajustement d'objectif", idobjet=ajustement.pk, classe="AjustementObjectifCollaborateur")
    ajustement.delete()
    return Get_objectif(request)


@Verifie_permission
def Reporter_solde(request):
    collaborateur = Get_collaborateur(request, modifiable=True)
    if not collaborateur:
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier ce collaborateur"}, status=403)
    parametres = utils_objectif.Get_parametres()
    periode = Get_periode_demandee(request, collaborateur.pk, parametres)
    ajustement = utils_objectif.Reporter_solde(idcollaborateur=collaborateur.pk, periode=periode, parametres=parametres, utilisateur=request.user)
    if not ajustement:
        return JsonResponse({"erreur": "Ce collaborateur n'a pas d'objectif sur cette période"}, status=400)
    suivante = utils_objectif.Periode_suivante(periode, parametres)
    return JsonResponse({"succes": True, "message": "%s : %s reporté sur %s" % (collaborateur.Get_nom(), ajustement.motif, suivante["libelle"])})


# ------------------------------------------------- Pages -------------------------------------------------

class Contexte_planning():
    def Get_contexte_planning(self, collaborateur=None, mode="page"):
        return {"pi_mode": mode, "pi_collaborateur": collaborateur,
                "pi_collaborateurs": [{"id": c.pk, "nom": c.Get_nom()} for c in Collaborateurs_accessibles(self.request.user)] if mode == "page" else []}


class View(CustomView, TemplateView, Contexte_planning):
    menu_code = "planning_individuel"
    template_name = "collaborateurs/planning_individuel.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Planning individuel"
        collaborateurs = Collaborateurs_accessibles(self.request.user)
        collaborateur = None
        if self.request.GET.get("idcollaborateur", "").isdigit():
            collaborateur = collaborateurs.filter(pk=int(self.request.GET["idcollaborateur"])).first()
        if not collaborateur:
            idcollaborateur = utils_parametres.Get(nom="dernier_collaborateur", categorie=CATEGORIE_PREFERENCES, utilisateur=self.request.user, valeur=0)
            collaborateur = collaborateurs.filter(pk=idcollaborateur).first() if idcollaborateur else None
        if not collaborateur:
            collaborateur = collaborateurs.first()
        if collaborateur:
            utils_parametres.Set(nom="dernier_collaborateur", categorie=CATEGORIE_PREFERENCES, utilisateur=self.request.user, valeur=collaborateur.pk)
        context.update(self.Get_contexte_planning(collaborateur, mode="page"))
        return context


class Onglet_planning(Onglet, DetailView, Contexte_planning):
    template_name = "collaborateurs/collaborateur_planning.html"

    def test_func_page(self):
        return super(Onglet_planning, self).test_func_page() and Peut_acceder(self.request.user)

    def get_context_data(self, **kwargs):
        context = super(Onglet_planning, self).get_context_data(**kwargs)
        context["onglet_actif"] = "planning"
        context["box_titre"] = "Planning individuel"
        context.update(self.Get_contexte_planning(self.object, mode="fiche"))
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs["idcollaborateur"])


# ------------------------------------------------- Soldes et reports -------------------------------------------------

class View_soldes(CustomView, TemplateView):
    menu_code = "soldes_objectifs_collaborateurs"
    template_name = "collaborateurs/soldes_objectifs.html"

    def get_context_data(self, **kwargs):
        context = super(View_soldes, self).get_context_data(**kwargs)
        context["page_titre"] = "Soldes et reports des objectifs"
        parametres = utils_objectif.Get_parametres()
        type_periode = self.request.GET.get("type_periode") if self.request.GET.get("type_periode") in ("CIVILE", "SCOLAIRE") else parametres["periode"]
        aujourdhui = datetime.date.today()
        annee_courante = utils_objectif.Annee_periode(aujourdhui, type_periode, parametres)
        try:
            annee = int(self.request.GET.get("annee") or 0)
        except ValueError:
            annee = 0
        if not 1900 < annee < 2200:
            # Par défaut : la dernière période terminée
            annee = annee_courante - 1
        periode = utils_objectif.Get_periode(annee, type_periode, parametres)
        suivante = utils_objectif.Periode_suivante(periode, parametres)
        origine = "%s:%s" % (periode["type"], periode["libelle"])

        ids_modifiables = utils_planning.Get_ids_modifiables(self.request.user)
        categories = {categorie.pk: categorie for categorie in TypeEvenementCollaborateur.objects.all()}
        from core.models import Ferie
        liste_feries = list(Ferie.objects.all())
        reports = {ajustement.collaborateur_id: ajustement for ajustement in AjustementObjectifCollaborateur.objects.filter(type="REPORT", periode_origine=origine)}
        lignes = []
        for collaborateur in Collaborateurs_accessibles(self.request.user):
            calcul = utils_objectif.Calcul_objectif(idcollaborateur=collaborateur.pk, periode=periode, parametres=parametres, date_reference=periode["fin"],
                                                    categories=categories, liste_feries=liste_feries)
            if not calcul.a_objectif:
                continue
            report = reports.get(collaborateur.pk)
            lignes.append({
                "collaborateur": collaborateur, "unite": calcul.unite, "modifiable": collaborateur.pk in ids_modifiables,
                "objectif": utils_objectif.Format_valeur(calcul.objectif, calcul.unite), "planifie": utils_objectif.Format_valeur(calcul.planifie, calcul.unite),
                "solde": utils_objectif.Format_valeur(calcul.solde, calcul.unite), "solde_valeur": calcul.solde,
                "report": utils_objectif.Format_valeur(float(report.valeur), calcul.unite) if report else None,
                "report_a_jour": bool(report) and abs(float(report.valeur) + calcul.solde) < 0.01,
            })

        context.update({"periode": periode, "suivante": suivante, "lignes": lignes, "type_periode": type_periode, "parametres": parametres,
                        "annees": list(range(annee_courante - 5, annee_courante + 2)), "en_cours": periode["fin"] >= aujourdhui})
        return context


@Verifie_permission
def Reporter_soldes(request):
    """ Report par lot des soldes de plusieurs collaborateurs """
    if not request.user.has_perm("core.soldes_objectifs_collaborateurs"):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de reporter les soldes"}, status=403)
    try:
        ids = [int(valeur) for valeur in json.loads(request.POST.get("collaborateurs", "[]"))]
        annee = int(request.POST.get("annee"))
    except (TypeError, ValueError):
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    parametres = utils_objectif.Get_parametres()
    type_periode = request.POST.get("type_periode") if request.POST.get("type_periode") in ("CIVILE", "SCOLAIRE") else parametres["periode"]
    periode = utils_objectif.Get_periode(annee, type_periode, parametres)
    ids_modifiables = utils_planning.Get_ids_modifiables(request.user)
    accessibles = set(Collaborateurs_accessibles(request.user).values_list("pk", flat=True))
    nbre = 0
    with transaction.atomic():
        for idcollaborateur in ids:
            if idcollaborateur not in ids_modifiables or idcollaborateur not in accessibles:
                continue
            if utils_objectif.Reporter_solde(idcollaborateur=idcollaborateur, periode=periode, parametres=parametres, utilisateur=request.user):
                nbre += 1
    return JsonResponse({"succes": True, "nbre": nbre})


# ------------------------------------------------- Impression, email, Excel et agenda -------------------------------------------------

TYPES_IMPRESSION = ("annuel", "bilan", "calendrier", "individuel", "recapitulatif")


def Get_parametres_edition(request, collaborateur=None):
    """ Paramètres d'édition : type de document, dates (toute la période, plage de mois ou jours sélectionnés) et options """
    parametres = utils_objectif.Get_parametres()
    periode = Get_periode_demandee(request, collaborateur.pk, parametres)
    type_document = request.POST.get("type") if request.POST.get("type") in TYPES_IMPRESSION else "annuel"
    toutes = [periode["debut"] + datetime.timedelta(days=n) for n in range((periode["fin"] - periode["debut"]).days + 1)]
    portee = request.POST.get("portee", "periode")
    dates = toutes
    if type_document not in ("annuel", "bilan"):
        if portee == "mois":
            try:
                debut = datetime.datetime.strptime(request.POST.get("mois_debut", ""), "%Y-%m").date()
                fin = datetime.datetime.strptime(request.POST.get("mois_fin", ""), "%Y-%m").date()
            except ValueError:
                return None, "Mois incorrects"
            if fin < debut:
                debut, fin = fin, debut
            fin = fin.replace(day=calendar.monthrange(fin.year, fin.month)[1])
            dates = [date for date in toutes if debut <= date <= fin]
        elif portee == "selection":
            try:
                selection = {Parse_date(valeur) for valeur in json.loads(request.POST.get("dates", "[]"))}
            except (TypeError, ValueError):
                selection = set()
            dates = [date for date in toutes if date in selection]
    if not dates:
        return None, "Aucune date à éditer"
    return {"dates": dates, "collaborateurs": [collaborateur.pk], "type": type_document, "periode": periode,
            "afficher_realise": request.POST.get("afficher_realise") == "true",
            "afficher_affectations": request.POST.get("afficher_affectations", "true") == "true",
            "afficher_notes": request.POST.get("afficher_notes", "true") == "true"}, None


@Verifie_permission
def Imprimer(request):
    collaborateur = Get_collaborateur(request)
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    parametres, erreur = Get_parametres_edition(request, collaborateur)
    if erreur:
        return JsonResponse({"erreur": erreur}, status=400)
    from collaborateurs.utils import utils_impression_planning
    titre = "%s - %s" % (utils_impression_planning.TYPES_DOCUMENTS[parametres["type"]][0], collaborateur.Get_nom())
    impression = utils_impression_planning.Impression(titre=titre, dict_donnees=parametres)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=400)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


@Verifie_permission
def Envoyer_email(request):
    """ Prépare un email au collaborateur avec le document en pièce jointe et ouvre l'éditeur d'emails """
    from core.models import Mail, Destinataire, DocumentJoint, ModeleEmail
    collaborateur = Get_collaborateur(request)
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    adresse = collaborateur.travail_mail or collaborateur.mail
    if not adresse:
        return JsonResponse({"erreur": "Ce collaborateur n'a pas d'adresse email (fiche collaborateur > Coordonnées)"}, status=400)
    parametres, erreur = Get_parametres_edition(request, collaborateur)
    if erreur:
        return JsonResponse({"erreur": erreur}, status=400)
    from collaborateurs.utils import utils_impression_planning
    nom_document = utils_impression_planning.TYPES_DOCUMENTS[parametres["type"]][0]
    impression = utils_impression_planning.Impression(titre="%s - %s" % (nom_document, collaborateur.Get_nom()), dict_donnees=parametres)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=400)

    dates = parametres["dates"]
    periode = parametres["periode"]["libelle"] if parametres["type"] in ("annuel", "bilan") else \
        ("du %s au %s" % (dates[0].strftime("%d/%m/%Y"), dates[-1].strftime("%d/%m/%Y")) if len(dates) > 1 else "du %s" % dates[0].strftime("%d/%m/%Y"))
    modele_email = ModeleEmail.objects.filter(categorie="saisie_libre", defaut=True).first()
    mail = Mail.objects.create(
        categorie="saisie_libre",
        objet=modele_email.objet if modele_email else "%s %s" % (nom_document, periode),
        html=modele_email.html if modele_email else "<p>Bonjour,</p><p>Veuillez trouver ci-joint votre document : %s (%s).</p><p>Cordialement.</p>" % (nom_document.lower(), periode),
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )
    destinataire = Destinataire.objects.create(categorie="collaborateur", collaborateur=collaborateur, adresse=adresse, valeurs=json.dumps({}))
    document_joint = DocumentJoint.objects.create(nom=nom_document, fichier=impression.Get_nom_fichier())
    destinataire.documents.add(document_joint)
    mail.destinataires.add(destinataire)
    return JsonResponse({"url": reverse("editeur_emails", kwargs={"pk": mail.pk})})


@Verifie_permission
def Exporter_excel(request):
    collaborateur = Get_collaborateur(request)
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    from collaborateurs.utils import utils_export_planning
    if request.POST.get("export") == "paie":
        parametres, erreur = Get_parametres_edition(request, collaborateur)
        if erreur:
            return JsonResponse({"erreur": erreur}, status=400)
        return JsonResponse({"url": utils_export_planning.Exporter(dates=parametres["dates"], collaborateurs=[collaborateur.pk])})
    periode = Get_periode_demandee(request, collaborateur.pk, utils_objectif.Get_parametres())
    return JsonResponse({"url": utils_export_planning.Exporter_bilan(collaborateur=collaborateur, periode=periode)})


@Verifie_permission
def Get_lien_ical(request):
    """ Lien secret de l'agenda iCal du collaborateur (mêmes règles que le planning général) """
    collaborateur = Get_collaborateur(request, modifiable=True)
    if not collaborateur:
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de gérer l'agenda de ce collaborateur"}, status=403)
    action = request.POST.get("action")
    if action == "revoquer":
        collaborateur.token_ical = None
        collaborateur.save(update_fields=["token_ical"])
        return JsonResponse({"url": None})
    if not collaborateur.token_ical or action == "regenerer":
        collaborateur.token_ical = secrets.token_urlsafe(32)
        collaborateur.save(update_fields=["token_ical"])
    return JsonResponse({"url": request.build_absolute_uri(reverse("planning_equipe_ical", kwargs={"token": collaborateur.token_ical}))})
