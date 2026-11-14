# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json, secrets
logger = logging.getLogger(__name__)
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404
from django.views.generic import TemplateView
from django.db import transaction
from django.urls import reverse
from core.views.base import CustomView
from core.models import Collaborateur, TypeEvenementCollaborateur, ModelePlanningCollaborateur, GroupeCollaborateurs, TypeQualificationCollaborateur, \
                        ContratCollaborateur, NotePlanningCollaborateur, EvenementCollaborateur, AffectationCollaborateur, Mail, Destinataire, DocumentJoint, ModeleEmail
from core.utils import utils_parametres
from collaborateurs.utils import utils_planning, utils_controle_reglementaire
from collaborateurs.utils.utils_planning import Parse_date, PERMISSION, CATEGORIE_PARAMETRES
from collaborateurs.utils.utils_affectations import Arbre


def Verifie_permission(function):
    def _function(request, *args, **kwargs):
        if not request.user.has_perm(PERMISSION):
            return HttpResponseForbidden()
        return function(request, *args, **kwargs)
    return _function


def Get_liste_ids(request, nom="collaborateurs"):
    try:
        return [int(valeur) for valeur in json.loads(request.POST.get(nom, "[]"))]
    except (TypeError, ValueError):
        return []


def Get_liste_dates(request, nom="dates"):
    try:
        return sorted(set(Parse_date(valeur) for valeur in json.loads(request.POST.get(nom, "[]"))))
    except (TypeError, ValueError):
        return []


# ------------------------------------------------- Données -------------------------------------------------

@Verifie_permission
def Get_donnees(request):
    """ Données de référence du planning """
    ids_modifiables = utils_planning.Get_ids_modifiables(request.user)

    contrats = {}
    for contrat in ContratCollaborateur.objects.all().order_by("date_debut"):
        contrats.setdefault(contrat.collaborateur_id, []).append({"d": str(contrat.date_debut), "f": str(contrat.date_fin) if contrat.date_fin else None,
                                                                  "h": float(contrat.heures_hebdo) if contrat.heures_hebdo else None})
    postes = {contrat.collaborateur_id: contrat.type_poste.nom for contrat in ContratCollaborateur.objects.select_related("type_poste").order_by("date_debut")}

    collaborateurs = []
    for collaborateur in Collaborateur.objects.prefetch_related("groupes", "qualifications").order_by("nom", "prenom"):
        collaborateurs.append({
            "id": collaborateur.pk, "nom": collaborateur.nom, "prenom": collaborateur.prenom or "", "poste": postes.get(collaborateur.pk, ""),
            "groupes": [groupe.pk for groupe in collaborateur.groupes.all()], "qualifications": [qualification.pk for qualification in collaborateur.qualifications.all()],
            "contrats": contrats.get(collaborateur.pk, []), "modifiable": collaborateur.pk in ids_modifiables,
            "mail": bool(collaborateur.travail_mail or collaborateur.mail),
        })

    affichage = utils_parametres.Get(nom="affichage", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur={}) or {}

    return JsonResponse({
        "categories": [{"id": categorie.pk, "nom": categorie.nom, "couleur": categorie.couleur, "type": categorie.type, "chevauchement": categorie.chevauchement_possible}
                       for categorie in TypeEvenementCollaborateur.objects.all().order_by("nom")],
        "affectations": Arbre().Get_liste_dict(),
        "collaborateurs": collaborateurs,
        "groupes": [{"id": groupe.pk, "nom": groupe.nom} for groupe in GroupeCollaborateurs.objects.all().order_by("nom")],
        "qualifications": [{"id": qualification.pk, "nom": qualification.nom} for qualification in TypeQualificationCollaborateur.objects.all().order_by("nom")],
        "modeles": [{"id": modele.pk, "nom": modele.nom, "nb_semaines": modele.nb_semaines, "cycle": modele.Get_libelle_cycle()} for modele in ModelePlanningCollaborateur.objects.all().order_by("nom")],
        "reglages": utils_planning.Get_reglages(request.user),
        "peut_regler_tous": utils_planning.Peut_regler_pour_tous(request.user),
        "affichage": affichage,
        "aujourdhui": str(datetime.date.today()),
    })


@Verifie_permission
def Get_evenements(request):
    date_debut = Parse_date(request.POST["date_debut"])
    date_fin = Parse_date(request.POST["date_fin"])
    if not date_debut or not date_fin or date_fin < date_debut or (date_fin - date_debut).days > 400:
        return JsonResponse({"erreur": "Période incorrecte"}, status=400)
    collaborateurs = None if request.POST.get("collaborateurs", "tous") == "tous" else Get_liste_ids(request)
    evenements = [utils_planning.Serialiser_evenement(evenement) for evenement in utils_planning.Get_evenements(date_debut, date_fin, collaborateurs)]
    notes = [{"date": str(note.date), "aff": note.affectation_id, "texte": note.texte} for note in NotePlanningCollaborateur.objects.filter(date__gte=date_debut, date__lte=date_fin)]
    resultat = {"evenements": evenements, "notes": notes, "remplissages": utils_planning.Get_remplissages(date_debut, date_fin),
                "date_debut": str(date_debut), "date_fin": str(date_fin)}
    resultat.update(utils_planning.Get_dates_speciales(date_debut, date_fin))
    return JsonResponse(resultat)


@Verifie_permission
def Get_anomalies(request):
    """ Contrôle réglementaire : anomalies des collaborateurs sur la période (avec éventuellement des évènements simulés non enregistrés) """
    date_debut = Parse_date(request.POST.get("date_debut"))
    date_fin = Parse_date(request.POST.get("date_fin"))
    if not date_debut or not date_fin or date_fin < date_debut or (date_fin - date_debut).days > 400:
        return JsonResponse({"erreur": "Période incorrecte"}, status=400)
    collaborateurs = None if request.POST.get("collaborateurs", "tous") == "tous" else Get_liste_ids(request)
    simulation = utils_controle_reglementaire.Lire_simulation(request.POST.get("simulation"))
    if simulation is None:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    anomalies = utils_controle_reglementaire.Get_anomalies(date_debut=date_debut, date_fin=date_fin, collaborateurs=collaborateurs,
                                                           simulation=simulation, supprimes=Get_liste_ids(request, "supprimes"))
    return JsonResponse({"anomalies": anomalies})


@Verifie_permission
def Memoriser_affichage(request):
    try:
        affichage = json.loads(request.POST.get("affichage", "{}"))
    except ValueError:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    utils_parametres.Set(nom="affichage", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur=affichage)
    return JsonResponse({"succes": True})


@Verifie_permission
def Memoriser_reglages(request):
    portee = request.POST.get("portee", "utilisateur")
    try:
        reglages = utils_planning.Nettoyer_reglages(json.loads(request.POST.get("reglages", "{}")))
    except ValueError:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    if portee == "tous":
        if not utils_planning.Peut_regler_pour_tous(request.user):
            return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de modifier les réglages de tous les utilisateurs"}, status=403)
        utils_parametres.Set(nom="reglages", categorie=CATEGORIE_PARAMETRES, utilisateur=None, valeur=reglages)
        # Les réglages personnels de l'utilisateur sont supprimés pour qu'il voie les nouveaux réglages par défaut
        utils_parametres.Set(nom="reglages", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur={})
    elif portee == "reinitialiser":
        utils_parametres.Set(nom="reglages", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur={})
    else:
        utils_parametres.Set(nom="reglages", categorie=CATEGORIE_PARAMETRES, utilisateur=request.user, valeur=reglages)
    return JsonResponse({"succes": True, "reglages": utils_planning.Get_reglages(request.user)})


# ------------------------------------------------- Enregistrement -------------------------------------------------

@Verifie_permission
def Enregistrer(request):
    try:
        operations = json.loads(request.POST.get("operations", "[]"))
    except ValueError:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    if not operations:
        return JsonResponse({"crees": {}, "maj": {}, "supprimes": []})

    try:
        with transaction.atomic():
            resultat = utils_planning.Enregistrer_operations(operations=operations, user=request.user)
            if "conflits" in resultat:
                transaction.set_rollback(True)
    except utils_planning.Erreur_enregistrement as erreur:
        return JsonResponse({"erreur": str(erreur)}, status=409)

    if "conflits" in resultat:
        # Renvoie l'état actuel des évènements en conflit pour mettre à jour l'affichage
        actuels = {evenement.pk: utils_planning.Serialiser_evenement(evenement) for evenement in EvenementCollaborateur.objects.filter(pk__in=resultat["conflits"])}
        return JsonResponse({"erreur": "Le planning a été modifié par un autre utilisateur entre-temps. L'affichage a été actualisé, recommencez votre modification.",
                             "conflits": resultat["conflits"], "actuels": actuels}, status=409)
    return JsonResponse(resultat)


@Verifie_permission
def Appliquer_modele(request):
    modeles = Get_liste_ids(request, "modeles")
    collaborateurs = Get_liste_ids(request)
    dates = Get_liste_dates(request)
    if not modeles or not collaborateurs or not dates:
        return JsonResponse({"erreur": "Sélectionnez au moins un modèle, un collaborateur et une date"}, status=400)
    if len(dates) > 400:
        return JsonResponse({"erreur": "La période est trop longue"}, status=400)
    apercu = request.POST.get("apercu") == "true"
    from collaborateurs.utils.utils_modeles_planning import Generateur, Get_departs, Repartir, Memoriser_recents
    generateur = Generateur(modeles=modeles, dates=dates, departs=Get_departs(request))
    repartition, messages_restriction = Repartir(modeles=modeles, collaborateurs=collaborateurs, date=dates[0], forcer=request.POST.get("forcer") == "true")
    nouveaux, hors_contrat = utils_planning.Generer_depuis_modeles(generateur=generateur, repartition=repartition, modeles=modeles, collaborateurs=collaborateurs, dates=dates)
    with transaction.atomic():
        resultat = utils_planning.Creer_par_lot(nouveaux=nouveaux, collaborateurs=collaborateurs, dates=dates, conflit=request.POST.get("conflit", "ignorer"),
                                                apercu=apercu, user=request.user, libelle="modèle de planning")
        if not apercu:
            generateur.Memoriser_ancrages()
            Memoriser_recents(request.user, modeles)
    resultat["nbre_hors_contrat"] = hors_contrat
    resultat["messages_restriction"] = messages_restriction
    return JsonResponse(resultat)


@Verifie_permission
def Copier_periode(request):
    source_debut = Parse_date(request.POST.get("source_debut"))
    source_fin = Parse_date(request.POST.get("source_fin"))
    destination_debut = Parse_date(request.POST.get("destination_debut"))
    collaborateurs = Get_liste_ids(request)
    if not source_debut or not source_fin or not destination_debut or source_fin < source_debut or not collaborateurs:
        return JsonResponse({"erreur": "Paramètres de copie incorrects"}, status=400)
    if (source_fin - source_debut).days > 92:
        return JsonResponse({"erreur": "La période copiée ne peut pas dépasser 3 mois"}, status=400)
    if destination_debut == source_debut:
        return JsonResponse({"erreur": "La date de destination doit être différente de la date de début de la période copiée"}, status=400)
    apercu = request.POST.get("apercu") == "true"
    nouveaux, dates_destination = utils_planning.Generer_copie(source_debut, source_fin, destination_debut, collaborateurs)
    with transaction.atomic():
        resultat = utils_planning.Creer_par_lot(nouveaux=nouveaux, collaborateurs=collaborateurs, dates=dates_destination, conflit=request.POST.get("conflit", "ignorer"),
                                                apercu=apercu, user=request.user, libelle="copie de période")
    return JsonResponse(resultat)


@Verifie_permission
def Enregistrer_note(request):
    date = Parse_date(request.POST.get("date"))
    if not date:
        return JsonResponse({"erreur": "Date incorrecte"}, status=400)
    idaffectation = int(request.POST.get("affectation") or 0) or None
    if idaffectation and not AffectationCollaborateur.objects.filter(pk=idaffectation).exists():
        return JsonResponse({"erreur": "Cette affectation n'existe plus"}, status=400)
    texte = (request.POST.get("texte") or "").strip()[:5000]
    notes = NotePlanningCollaborateur.objects.filter(date=date, affectation_id=idaffectation)
    if texte:
        note = notes.first() or NotePlanningCollaborateur(date=date, affectation_id=idaffectation)
        note.texte, note.utilisateur = texte, request.user
        note.save()
        notes.exclude(pk=note.pk).delete()
    else:
        notes.delete()
    return JsonResponse({"succes": True, "date": str(date), "aff": idaffectation, "texte": texte})


# ------------------------------------------------- Diffusion -------------------------------------------------

def Get_parametres_edition(request):
    dates = Get_liste_dates(request)
    collaborateurs = Get_liste_ids(request)
    if not dates or not collaborateurs:
        return None
    from collaborateurs.utils.utils_impression_planning import TYPES_DOCUMENTS
    type_document = request.POST.get("type", "individuel")
    if type_document not in TYPES_DOCUMENTS:
        type_document = "individuel"
    return {"dates": dates, "collaborateurs": collaborateurs, "type": type_document,
            "afficher_realise": request.POST.get("afficher_realise") == "true",
            "afficher_affectations": request.POST.get("afficher_affectations", "true") == "true",
            "afficher_notes": request.POST.get("afficher_notes", "true") == "true",
            "grouper_affectations": request.POST.get("grouper_affectations") == "true"}


@Verifie_permission
def Imprimer(request):
    parametres = Get_parametres_edition(request)
    if not parametres:
        return JsonResponse({"erreur": "Aucune date ou aucun collaborateur à imprimer"}, status=400)
    from collaborateurs.utils import utils_impression_planning
    titre = utils_impression_planning.TYPES_DOCUMENTS[parametres["type"]][0]
    impression = utils_impression_planning.Impression(titre=titre, dict_donnees=parametres)
    if impression.erreurs:
        return JsonResponse({"erreur": impression.erreurs[0]}, status=400)
    return JsonResponse({"nom_fichier": impression.Get_nom_fichier()})


@Verifie_permission
def Envoyer_emails(request):
    parametres = Get_parametres_edition(request)
    if not parametres:
        return JsonResponse({"erreur": "Aucune date ou aucun collaborateur"}, status=400)
    from collaborateurs.utils import utils_impression_planning
    if not utils_impression_planning.TYPES_DOCUMENTS[parametres["type"]][2]:
        parametres["type"] = "individuel"
    nom_document = utils_impression_planning.TYPES_DOCUMENTS[parametres["type"]][0]
    dates = parametres["dates"]
    periode = "du %s au %s" % (dates[0].strftime("%d/%m/%Y"), dates[-1].strftime("%d/%m/%Y")) if len(dates) > 1 else "du %s" % dates[0].strftime("%d/%m/%Y")

    modele_email = ModeleEmail.objects.filter(categorie="saisie_libre", defaut=True).first()
    mail = Mail.objects.create(
        categorie="saisie_libre",
        objet=modele_email.objet if modele_email else "Votre planning %s" % periode,
        html=modele_email.html if modele_email else "<p>Bonjour,</p><p>Veuillez trouver ci-joint votre planning %s.</p><p>Cordialement.</p>" % periode,
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    sans_adresse = []
    for collaborateur in Collaborateur.objects.filter(pk__in=parametres["collaborateurs"]).order_by("nom", "prenom"):
        adresse = collaborateur.travail_mail or collaborateur.mail
        if not adresse:
            sans_adresse.append(collaborateur.Get_nom())
            continue
        parametres_collaborateur = dict(parametres, collaborateurs=[collaborateur.pk])
        impression = utils_impression_planning.Impression(titre="Planning de %s" % collaborateur.Get_nom(), dict_donnees=parametres_collaborateur)
        if impression.erreurs:
            continue
        destinataire = Destinataire.objects.create(categorie="collaborateur", collaborateur=collaborateur, adresse=adresse, valeurs=json.dumps({}))
        document_joint = DocumentJoint.objects.create(nom=nom_document, fichier=impression.Get_nom_fichier())
        destinataire.documents.add(document_joint)
        mail.destinataires.add(destinataire)

    if not mail.destinataires.exists():
        mail.delete()
        return JsonResponse({"erreur": "Aucun des collaborateurs sélectionnés n'a d'adresse email"}, status=400)
    return JsonResponse({"url": reverse("editeur_emails", kwargs={"pk": mail.pk}), "sans_adresse": sans_adresse})


@Verifie_permission
def Exporter_recapitulatif(request):
    parametres = Get_parametres_edition(request)
    if not parametres:
        return JsonResponse({"erreur": "Aucune date ou aucun collaborateur"}, status=400)
    from collaborateurs.utils import utils_export_planning
    url = utils_export_planning.Exporter(dates=parametres["dates"], collaborateurs=parametres["collaborateurs"])
    return JsonResponse({"url": url})


@Verifie_permission
def Get_lien_ical(request):
    collaborateur = Collaborateur.objects.filter(pk=int(request.POST.get("idcollaborateur", 0))).first()
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    if collaborateur.pk not in utils_planning.Get_ids_modifiables(request.user):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de gérer le planning de ce collaborateur"}, status=403)
    if request.POST.get("action") == "revoquer":
        collaborateur.token_ical = None
        collaborateur.save(update_fields=["token_ical"])
        return JsonResponse({"url": None})
    if not collaborateur.token_ical or request.POST.get("action") == "regenerer":
        collaborateur.token_ical = secrets.token_urlsafe(32)
        collaborateur.save(update_fields=["token_ical"])
    url = request.build_absolute_uri(reverse("planning_equipe_ical", kwargs={"token": collaborateur.token_ical}))
    return JsonResponse({"url": url})


def Ical(request, token=""):
    """ Agenda iCal d'un collaborateur, accessible sans authentification par son lien secret """
    if not token or len(token) < 20:
        raise Http404
    collaborateur = Collaborateur.objects.filter(token_ical=token).first()
    if not collaborateur:
        raise Http404
    from collaborateurs.utils import utils_export_planning
    contenu = utils_export_planning.Generer_ical(collaborateur)
    reponse = HttpResponse(contenu, content_type="text/calendar; charset=utf-8")
    reponse["Content-Disposition"] = 'inline; filename="planning.ics"'
    return reponse


class View(CustomView, TemplateView):
    menu_code = "planning_equipe"
    template_name = "collaborateurs/planning_equipe.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Planning général"
        return context
