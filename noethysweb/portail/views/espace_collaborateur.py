# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Espace collaborateur du portail : planning, congés, documents et heures réalisées du collaborateur connecté """

import datetime, json, os, logging, html
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.http import JsonResponse, FileResponse, Http404, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from core.decorators import secure_ajax_collaborateur
from collaborateurs.utils import utils_espace_collaborateur
from core.models import Collaborateur, EvenementCollaborateur, TypeEvenementCollaborateur, ContratCollaborateur, TypeCongeCollaborateur, \
                        DemandeAbsenceCollaborateur, PieceCollaborateur, TypePieceCollaborateur, Historique, Ferie
from core.utils import utils_dates
from collaborateurs.utils import utils_conges, utils_planning, utils_pieces_manquantes
from collaborateurs.utils.utils_affectations import Arbre
from portail.views.base import CustomView
from portail.views.menu import Menu

EXTENSIONS_PIECES = ("pdf", "jpg", "jpeg", "png", "heic", "webp")
TAILLE_MAX_PIECE = 10 * 1024 * 1024
MAX_PIECES_PAR_JOUR = 20        # Limite anti-abus : pièces transmises par un collaborateur sur 24 heures
MAX_DEMANDES_ATTENTE = 20       # Limite anti-abus : demandes d'absence en attente simultanément
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def Get_menu_collaborateur(parametres_portail={}, user=None):
    menu = Menu(titre="Menu principal", user=user)
    menu.Add(code="portail_collaborateur_accueil", titre="Accueil", icone="bi bi-house-door", toujours_afficher=True)
    menu.Add(code="portail_collaborateur_planning", titre="Mon planning", icone="bi bi-calendar4-week", toujours_afficher=True)
    if TypeCongeCollaborateur.objects.exists():
        menu.Add(code="portail_collaborateur_conges", titre="Mes congés", icone="bi bi-airplane", toujours_afficher=True)
    menu.Add(code="portail_collaborateur_documents", titre="Mes documents", icone="bi bi-file-earmark-text", toujours_afficher=True)
    if parametres_portail.get("collaborateurs_saisie_realise", False):
        menu.Add(code="portail_collaborateur_heures", titre="Mes heures réalisées", icone="bi bi-stopwatch", toujours_afficher=True)
    menu.Add(code="portail_mentions", titre="Mentions légales", icone="bi bi-info-circle", toujours_afficher=parametres_portail.get("mentions_afficher_page", False))
    return menu


def Lire_date_reference(texte=""):
    """ Date de référence demandée dans l'URL, bornée à une plage raisonnable (évite les dépassements de capacité sur les dates extrêmes) """
    try:
        date = datetime.datetime.strptime(texte or "", "%Y-%m-%d").date()
    except ValueError:
        return datetime.date.today()
    return date if 2000 <= date.year <= 2100 else datetime.date.today()


def Texte_jour(date=None):
    return "%s %d %s" % (JOURS[date.weekday()], date.day, MOIS[date.month - 1])


def Texte_jour_court(date=None):
    return "%s %d" % (JOURS[date.weekday()][:3] + ".", date.day)


def Duree(minutes=0):
    minutes = int(round(minutes))
    return "%dh%02d" % (minutes // 60, minutes % 60)


class CustomViewCollaborateur(CustomView):
    """ Pages de l'espace collaborateur : réservées aux comptes collaborateur actifs, espace activé. Le collaborateur est toujours celui de la session. """
    espace_collaborateur = True
    parametre_requis = None

    def test_func(self):
        if self.request.user.categorie != "collaborateur":
            return False
        collaborateur = Collaborateur.objects.filter(utilisateur=self.request.user, internet_actif=True).first()
        if not collaborateur:
            return False
        parametres = utils_espace_collaborateur.Get_parametres()
        if not utils_espace_collaborateur.Espace_actif(parametres):
            return False
        if self.parametre_requis and not parametres.get(self.parametre_requis, False):
            return False
        return True

    def get_collaborateur(self):
        if not hasattr(self, "_collaborateur"):
            self._collaborateur = Collaborateur.objects.get(utilisateur=self.request.user)
        return self._collaborateur

    def get_context_data(self, **kwargs):
        context = super(CustomViewCollaborateur, self).get_context_data(**kwargs)
        menu = Get_menu_collaborateur(parametres_portail=context["parametres_portail"], user=self.request.user)
        context["menu_principal"] = menu
        context["menu_actif"] = menu.Find(code=self.menu_code)
        context["breadcrumb"] = context["menu_actif"].GetBreadcrumb() if context["menu_actif"] else []
        context["collaborateur"] = self.get_collaborateur()
        context["autoriser_demandes"] = context["parametres_portail"].get("collaborateurs_demandes_absences", True)
        context["autoriser_depot"] = context["parametres_portail"].get("collaborateurs_depot_pieces", True)
        return context


def Get_evenements(collaborateur=None, date_debut=None, date_fin=None):
    """ Evènements du collaborateur regroupés par jour (un évènement de plusieurs jours apparaît chaque jour) """
    arbre = Arbre()
    jours = {}
    for evenement in utils_planning.Get_evenements(date_debut, date_fin, [collaborateur.pk]).select_related("type_evenement", "affectation"):
        date = max(evenement.date_debut.date(), date_debut)
        while date <= min((evenement.date_fin - datetime.timedelta(minutes=1)).date(), date_fin):
            jours.setdefault(date, []).append({
                "id": evenement.pk, "debut": evenement.date_debut, "fin": evenement.date_fin, "categorie": evenement.type_evenement.nom, "couleur": evenement.type_evenement.couleur,
                "travail": evenement.type_evenement.type == "ADDITION", "titre": evenement.titre or "",
                "affectation": arbre.Get_chemin(evenement.affectation_id) if evenement.affectation_id else "",
                "journee_entiere": evenement.date_debut.date() < date < evenement.date_fin.date(),
                "realise": "%s–%s" % (evenement.realise_debut.strftime("%Hh%M"), evenement.realise_fin.strftime("%Hh%M")) if evenement.realise_debut and evenement.realise_fin else "",
                "rd": evenement.realise_debut, "rf": evenement.realise_fin, "dd": evenement.declare_debut, "df": evenement.declare_fin, "declare_etat": evenement.declare_etat,
            })
            date += datetime.timedelta(days=1)
    return jours


def Minutes_travail(evenements=[]):
    return sum((evt["fin"] - evt["debut"]).total_seconds() / 60 for evt in evenements if evt["travail"])


def Heures_contrat_semaine(collaborateur=None, date=None):
    contrat = ContratCollaborateur.objects.filter(collaborateur=collaborateur, date_debut__lte=date).exclude(date_fin__lt=date).order_by("-date_debut").first()
    return float(contrat.heures_hebdo) * 60 if contrat and contrat.heures_hebdo else None


def Get_conges(collaborateur=None):
    types = [type_conge for type_conge in TypeCongeCollaborateur.objects.select_related("categorie").order_by("ordre", "nom") if type_conge.actif]
    compteurs = utils_conges.Get_compteurs([collaborateur.pk], types)
    return [compteurs[(collaborateur.pk, type_conge.pk)] for type_conge in types]


def Get_pieces(collaborateur=None):
    """ Pièces du collaborateur avec leur état de validité """
    aujourdhui = datetime.date.today()
    pieces = []
    for piece in PieceCollaborateur.objects.select_related("type_piece").filter(collaborateur=collaborateur).order_by("-date_depot", "-date_debut"):
        if piece.statut == "ATTENTE":
            etat, classe = "En cours de vérification", "info"
        elif piece.statut == "REFUSEE":
            etat, classe = "Refusée", "secondary"
        elif piece.date_fin and piece.date_fin < aujourdhui:
            etat, classe = "Expirée", "danger"
        elif piece.date_fin and (piece.date_fin - aujourdhui).days <= 30:
            etat, classe = "Expire bientôt", "warning"
        else:
            etat, classe = "Valide", "success"
        pieces.append({"piece": piece, "nom": piece.type_piece.nom if piece.type_piece else (piece.titre or "Document"), "etat": etat, "classe": classe})
    return pieces


# ------------------------------------------------- Pages -------------------------------------------------

class Accueil(CustomViewCollaborateur, TemplateView):
    template_name = "portail/collaborateur/accueil.html"
    menu_code = "portail_collaborateur_accueil"

    def get_context_data(self, **kwargs):
        context = super(Accueil, self).get_context_data(**kwargs)
        context["page_titre"] = "Accueil"
        collaborateur = context["collaborateur"]
        aujourdhui = datetime.date.today()
        lundi = aujourdhui - datetime.timedelta(days=aujourdhui.weekday())
        evenements = Get_evenements(collaborateur, lundi, lundi + datetime.timedelta(days=13))
        context["jours"] = [{"date": date, "texte": Texte_jour(date), "libelle": libelle, "evenements": evenements.get(date, [])}
                            for date, libelle in ((aujourdhui, "Aujourd'hui"), (aujourdhui + datetime.timedelta(days=1), "Demain"))]
        semaine = [evt for date in (lundi + datetime.timedelta(days=n) for n in range(7)) for evt in evenements.get(date, [])]
        context["semaine_total"] = Duree(Minutes_travail(semaine))
        contrat = Heures_contrat_semaine(collaborateur, aujourdhui)
        context["semaine_contrat"] = Duree(contrat) if contrat else None
        prochain = next((date for date in sorted(evenements) if date > aujourdhui + datetime.timedelta(days=1) and any(evt["travail"] for evt in evenements[date])), None)
        context["prochain_jour"] = {"texte": Texte_jour(prochain), "evenements": evenements[prochain]} if prochain else None
        context["conges"] = Get_conges(collaborateur)
        context["nb_demandes_attente"] = DemandeAbsenceCollaborateur.objects.filter(collaborateur=collaborateur, etat="ATTENTE").count()
        context["pieces_manquantes"] = [piece for piece in utils_pieces_manquantes.Get_pieces_manquantes(collaborateur=collaborateur) if not piece["valide"]]
        context["pieces_alerte"] = [piece for piece in Get_pieces(collaborateur) if piece["classe"] == "warning" and piece["piece"].statut == "VALIDE"]
        context["nb_documents"] = len(context["pieces_manquantes"]) + len(context["pieces_alerte"])
        # Modifications récentes du planning (14 derniers jours)
        context["modifications"] = Historique.objects.filter(collaborateur=collaborateur, titre__in=("Ajout d'un évènement", "Modification d'un évènement", "Suppression d'un évènement"),
                                                             horodatage__gte=datetime.datetime.now() - datetime.timedelta(days=14)).order_by("-horodatage")[:6]
        return context


class Planning(CustomViewCollaborateur, TemplateView):
    template_name = "portail/collaborateur/planning.html"
    menu_code = "portail_collaborateur_planning"

    def get_context_data(self, **kwargs):
        context = super(Planning, self).get_context_data(**kwargs)
        context["page_titre"] = "Mon planning"
        collaborateur = context["collaborateur"]
        vue = "mois" if self.request.GET.get("vue") == "mois" else "semaine"
        reference = Lire_date_reference(self.request.GET.get("date", ""))
        liste_feries = list(Ferie.objects.all())
        if vue == "semaine":
            debut = reference - datetime.timedelta(days=reference.weekday())
            fin = debut + datetime.timedelta(days=6)
            precedent, suivant = debut - datetime.timedelta(days=7), debut + datetime.timedelta(days=7)
            titre = "Du %d %s au %d %s %d" % (debut.day, MOIS[debut.month - 1], fin.day, MOIS[fin.month - 1], fin.year)
        else:
            debut = reference.replace(day=1)
            fin = (debut + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
            precedent, suivant = (debut - datetime.timedelta(days=1)).replace(day=1), fin + datetime.timedelta(days=1)
            titre = "%s %d" % (MOIS[debut.month - 1].capitalize(), debut.year)
        evenements = Get_evenements(collaborateur, debut, fin)
        jours = []
        date = debut
        while date <= fin:
            ferie = utils_dates.EstFerie(date, liste_feries)
            jours.append({"date": date, "texte": Texte_jour(date), "court": Texte_jour_court(date), "evenements": evenements.get(date, []), "aujourdhui": date == datetime.date.today(),
                          "ferie": ferie.nom if ferie else "", "we": date.weekday() >= 5, "total": Duree(Minutes_travail(evenements.get(date, [])))})
            date += datetime.timedelta(days=1)
        total = sum(Minutes_travail(jour["evenements"]) for jour in jours)
        contrat = Heures_contrat_semaine(collaborateur, debut)
        context.update({"vue": vue, "titre_periode": titre, "jours": jours, "total": Duree(total), "contrat": Duree(contrat) if contrat and vue == "semaine" else None,
                        "precedent": str(precedent), "suivant": str(suivant), "reference": str(reference),
                        "decalage_mois": range(debut.weekday()) if vue == "mois" else [], "jours_semaine": [jour[:3] for jour in JOURS]})
        context["lien_ical"] = self.request.build_absolute_uri(reverse("planning_equipe_ical", kwargs={"token": collaborateur.token_ical})) if collaborateur.token_ical else None
        return context


class Conges(CustomViewCollaborateur, TemplateView):
    template_name = "portail/collaborateur/conges.html"
    menu_code = "portail_collaborateur_conges"

    def get_context_data(self, **kwargs):
        context = super(Conges, self).get_context_data(**kwargs)
        context["page_titre"] = "Mes congés"
        collaborateur = context["collaborateur"]
        context["conges"] = Get_conges(collaborateur)
        context["demandes"] = [utils_conges.Serialiser_demande(demande, ids_modifiables=set()) for demande in DemandeAbsenceCollaborateur.objects.select_related(
            "type_conge__categorie", "collaborateur", "auteur", "decideur").filter(collaborateur=collaborateur).order_by("-date_debut")[:30]]
        return context


class Demande(CustomViewCollaborateur, TemplateView):
    template_name = "portail/collaborateur/conges_demande.html"
    menu_code = "portail_collaborateur_conges"
    parametre_requis = "collaborateurs_demandes_absences"

    def get_context_data(self, **kwargs):
        context = super(Demande, self).get_context_data(**kwargs)
        context["page_titre"] = "Demander une absence"
        context["types"] = TypeCongeCollaborateur.objects.filter(actif=True).order_by("ordre", "nom")
        context["aujourdhui"] = str(datetime.date.today())
        return context


class Documents(CustomViewCollaborateur, TemplateView):
    template_name = "portail/collaborateur/documents.html"
    menu_code = "portail_collaborateur_documents"

    def get_context_data(self, **kwargs):
        context = super(Documents, self).get_context_data(**kwargs)
        context["page_titre"] = "Mes documents"
        collaborateur = context["collaborateur"]
        context["pieces_fournir"] = utils_pieces_manquantes.Get_pieces_manquantes(collaborateur=collaborateur)
        context["pieces"] = Get_pieces(collaborateur)
        context["types_pieces"] = TypePieceCollaborateur.objects.order_by("nom")
        context["extensions"] = ", ".join(EXTENSIONS_PIECES)
        return context

    def post(self, request, *args, **kwargs):
        """ Transmission d'une pièce : elle reste en cours de vérification jusqu'à sa validation par un gestionnaire """
        if not utils_espace_collaborateur.Get_parametres().get("collaborateurs_depot_pieces", True):
            return HttpResponseRedirect(reverse("portail_collaborateur_documents"))
        collaborateur = self.get_collaborateur()
        fichier = request.FILES.get("document")
        erreur = None
        if not fichier:
            erreur = "Sélectionnez le fichier à transmettre"
        elif os.path.splitext(fichier.name)[1].lower().lstrip(".") not in EXTENSIONS_PIECES:
            erreur = "Type de fichier non autorisé (formats acceptés : %s)" % ", ".join(EXTENSIONS_PIECES)
        elif fichier.size > TAILLE_MAX_PIECE:
            erreur = "Le fichier est trop volumineux (10 Mo maximum)"
        elif PieceCollaborateur.objects.filter(collaborateur=collaborateur, statut="ATTENTE", date_depot__gte=datetime.datetime.now() - datetime.timedelta(days=1)).count() >= MAX_PIECES_PAR_JOUR:
            erreur = "Vous avez déjà transmis de nombreux documents aujourd'hui. Merci de réessayer demain ou de contacter votre responsable."
        type_piece = TypePieceCollaborateur.objects.filter(pk=request.POST.get("type_piece") or 0).first()
        try:
            date_debut = datetime.datetime.strptime(request.POST.get("date_debut", ""), "%Y-%m-%d").date() if request.POST.get("date_debut") else datetime.date.today()
            date_fin = datetime.datetime.strptime(request.POST.get("date_fin", ""), "%Y-%m-%d").date() if request.POST.get("date_fin") else datetime.date(2999, 1, 1)
        except ValueError:
            erreur = erreur or "Les dates de validité sont incorrectes"
        if not erreur and date_fin < date_debut:
            erreur = "La date de fin de validité doit être postérieure à la date de début"
        if erreur:
            messages.add_message(request, messages.ERROR, erreur)
            return HttpResponseRedirect(reverse("portail_collaborateur_documents"))
        titre = (request.POST.get("titre") or "").strip()[:200] or (None if type_piece else "Document transmis")
        piece = PieceCollaborateur.objects.create(collaborateur=collaborateur, type_piece=type_piece, titre=titre, date_debut=date_debut, date_fin=date_fin, document=fichier,
                                                  statut="ATTENTE", date_depot=datetime.datetime.now(), observations="Transmis depuis l'espace collaborateur")
        from core.utils import utils_historique
        utils_historique.Ajouter(titre="Transmission d'une pièce", detail=type_piece.nom if type_piece else titre, utilisateur=request.user, collaborateur=collaborateur.pk,
                                 objet="Pièce", idobjet=piece.pk, classe="PieceCollaborateur", portail=True)
        utils_espace_collaborateur.Notifier_a_verifier(collaborateur, "Document à vérifier pour %s" % collaborateur.Get_nom(),
                                                       "a transmis un document (%s) depuis son espace collaborateur." % html.escape(type_piece.nom if type_piece else titre),
                                                       "onglet Pièces de sa fiche", request=request)
        messages.add_message(request, messages.SUCCESS, "Votre document a été transmis. Il sera vérifié par votre responsable.")
        return HttpResponseRedirect(reverse("portail_collaborateur_documents"))


class Heures(CustomViewCollaborateur, TemplateView):
    template_name = "portail/collaborateur/heures.html"
    menu_code = "portail_collaborateur_heures"
    parametre_requis = "collaborateurs_saisie_realise"

    def get_context_data(self, **kwargs):
        context = super(Heures, self).get_context_data(**kwargs)
        context["page_titre"] = "Mes heures réalisées"
        collaborateur = context["collaborateur"]
        aujourdhui = datetime.date.today()
        try:
            semaines = max(0, min(1, int(self.request.GET.get("semaine", 0))))
        except ValueError:
            semaines = 0
        lundi = aujourdhui - datetime.timedelta(days=aujourdhui.weekday() + 7 * semaines)
        fin = min(lundi + datetime.timedelta(days=6), aujourdhui)
        evenements = Get_evenements(collaborateur, lundi, fin)
        lignes = []
        for date in sorted(evenements):
            for evt in evenements[date]:
                if evt["travail"] and evt["debut"].date() == date:
                    if evt["declare_etat"] == "ATTENTE":
                        arrivee, depart, etat = evt["dd"], evt["df"], ("warning", "Ecart à valider")
                    elif evt["rd"] and evt["rf"]:
                        arrivee, depart = evt["rd"], evt["rf"]
                        etat = ("success", "Enregistré") if (arrivee, depart) == (evt["debut"], evt["fin"]) else ("success", "Ecart validé")
                    else:
                        arrivee, depart, etat = evt["debut"], evt["fin"], ("light", "Non déclaré")
                    if evt["declare_etat"] == "REFUSEE":
                        etat = ("danger", "Ecart refusé")
                    lignes.append(dict(evt, jour=Texte_jour_court(date), arrivee=arrivee, depart=depart, etat_classe=etat[0], etat_texte=etat[1]))
        context.update({"lignes": lignes, "semaine": semaines, "titre_semaine": "Semaine du %d %s" % (lundi.day, MOIS[lundi.month - 1])})
        return context


# ------------------------------------------------- Actions -------------------------------------------------

class Planning_pdf(CustomViewCollaborateur, TemplateView):
    """ PDF du planning de la semaine ou du mois affiché """
    menu_code = "portail_collaborateur_planning"

    def get(self, request, *args, **kwargs):
        from collaborateurs.utils import utils_impression_planning, utils_objectif
        collaborateur = self.get_collaborateur()
        reference = Lire_date_reference(request.GET.get("date", ""))
        if request.GET.get("vue") == "mois":
            debut = reference.replace(day=1)
            fin = (debut + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        else:
            debut = reference - datetime.timedelta(days=reference.weekday())
            fin = debut + datetime.timedelta(days=6)
        parametres = utils_objectif.Get_parametres()
        type_periode = utils_objectif.Type_periode_defaut(collaborateur.pk, parametres, debut)
        periode = utils_objectif.Get_periode(utils_objectif.Annee_periode(debut, type_periode, parametres), type_periode, parametres)
        dates = [debut + datetime.timedelta(days=n) for n in range((fin - debut).days + 1)]
        impression = utils_impression_planning.Impression(titre="Planning de %s" % collaborateur.Get_nom(), dict_donnees={
            "dates": dates, "collaborateurs": [collaborateur.pk], "type": "individuel", "periode": periode,
            "afficher_realise": False, "afficher_affectations": True, "afficher_notes": False})
        if impression.erreurs:
            messages.add_message(request, messages.ERROR, impression.erreurs[0])
            return HttpResponseRedirect(reverse("portail_collaborateur_planning"))
        chemin = os.path.join(settings.MEDIA_ROOT, impression.Get_nom_fichier().lstrip("/"))
        return FileResponse(open(chemin, "rb"), as_attachment=True, filename="planning_%s.pdf" % debut.strftime("%Y-%m-%d"), content_type="application/pdf")


class Telecharger_piece(CustomViewCollaborateur, TemplateView):
    """ Téléchargement d'une pièce du collaborateur connecté uniquement """
    menu_code = "portail_collaborateur_documents"

    def get(self, request, *args, **kwargs):
        piece = PieceCollaborateur.objects.filter(pk=kwargs.get("idpiece"), collaborateur=self.get_collaborateur()).first()
        if not piece or not piece.document:
            raise Http404
        from django.utils.text import slugify
        nom = slugify(piece.Get_nom() or "document") or "document"
        return FileResponse(piece.document.open("rb"), as_attachment=True, filename=nom + os.path.splitext(piece.document.name)[1].lower())


def Lire_demande_portail(request, collaborateur=None):
    """ Demande saisie par le collaborateur connecté (le collaborateur ne vient jamais du formulaire) """
    type_conge = TypeCongeCollaborateur.objects.select_related("categorie").filter(pk=request.POST.get("idtype") or 0, actif=True).first()
    if not type_conge:
        raise utils_conges.Erreur("Sélectionnez un type d'absence")
    demande = DemandeAbsenceCollaborateur(collaborateur=collaborateur, type_conge=type_conge)
    try:
        demande.date_debut = utils_planning.Parse_date(request.POST.get("date_debut"))
        demande.date_fin = utils_planning.Parse_date(request.POST.get("date_fin")) or demande.date_debut
        demande.heure_debut = utils_conges.Heure(request.POST["heure_debut"]) if request.POST.get("heure_debut") else None
        demande.heure_fin = utils_conges.Heure(request.POST["heure_fin"]) if request.POST.get("heure_fin") else None
    except ValueError:
        raise utils_conges.Erreur("Les dates ou les heures saisies sont incorrectes")
    demande.debut_apres_midi = request.POST.get("debut_apres_midi") == "true" and not demande.heure_debut
    demande.fin_matin = request.POST.get("fin_matin") == "true" and not demande.heure_debut
    demande.motif = (request.POST.get("motif") or "").strip()[:2000] or None
    if demande.date_debut and demande.date_debut < datetime.date.today() - datetime.timedelta(days=31):
        raise utils_conges.Erreur("La date de début ne peut pas être antérieure de plus d'un mois")
    demande.quantite = utils_conges.Calculer_demande(demande)["quantite"]
    return demande


@secure_ajax_collaborateur
def Ajax_calculer_demande(request):
    collaborateur = request.user.collaborateur
    try:
        demande = Lire_demande_portail(request, collaborateur)
    except utils_conges.Erreur as erreur:
        return JsonResponse({"erreur": str(erreur)})
    compteur = utils_conges.Get_compteurs([collaborateur.pk], [demande.type_conge], annee=utils_conges.Annee_de(demande.type_conge, demande.date_debut))[(collaborateur.pk, demande.type_conge.pk)]
    apres = compteur["previsionnel"] - float(demande.quantite)
    return JsonResponse({"quantite_txt": utils_conges.Format_valeur(demande.quantite, demande.type_conge.unite), "periode": compteur["periode"], "nom": demande.type_conge.nom,
                         "solde_txt": compteur["solde_txt"], "attente_txt": compteur["attente_txt"] if compteur["attente"] else "",
                         "apres_txt": utils_conges.Format_valeur(apres, demande.type_conge.unite), "negatif": apres < -0.001, "bloquant": apres < -0.001 and not demande.type_conge.solde_negatif})


@secure_ajax_collaborateur
def Ajax_envoyer_demande(request):
    if not utils_espace_collaborateur.Get_parametres().get("collaborateurs_demandes_absences", True):
        return JsonResponse({"erreur": "Les demandes d'absence ne sont pas ouvertes"}, status=403)
    collaborateur = request.user.collaborateur
    if DemandeAbsenceCollaborateur.objects.filter(collaborateur=collaborateur, etat="ATTENTE").count() >= MAX_DEMANDES_ATTENTE:
        return JsonResponse({"erreur": "Vous avez déjà %d demandes en attente : patientez jusqu'à leur traitement" % MAX_DEMANDES_ATTENTE}, status=400)
    try:
        demande = Lire_demande_portail(request, collaborateur)
    except utils_conges.Erreur as erreur:
        return JsonResponse({"erreur": str(erreur)}, status=400)
    demande.auteur = request.user
    demande.save()
    utils_conges.Historique(demande, request.user, "Demande d'absence depuis l'espace collaborateur")
    utils_espace_collaborateur.Notifier_nouvelle_demande(demande, request=request)
    messages.add_message(request, messages.SUCCESS, "Votre demande a été envoyée. Vous serez prévenu(e) de la décision.")
    return JsonResponse({"url": reverse("portail_collaborateur_conges")})


@secure_ajax_collaborateur
def Ajax_annuler_demande(request):
    demande = DemandeAbsenceCollaborateur.objects.filter(pk=request.POST.get("iddemande") or 0, collaborateur=request.user.collaborateur, etat="ATTENTE").first()
    if not demande:
        return JsonResponse({"erreur": "Cette demande ne peut plus être annulée"}, status=404)
    utils_conges.Annuler(demande, request.user, restaurer=False, commentaire="Annulée par le collaborateur")
    messages.add_message(request, messages.SUCCESS, "Votre demande a été annulée.")
    return JsonResponse({"succes": True})


def Lire_heure_jour(texte="", jour=None):
    return datetime.datetime.combine(jour, datetime.datetime.strptime(texte, "%H:%M").time())


@secure_ajax_collaborateur
def Ajax_enregistrer_heures(request):
    """ Déclaration des heures réalisées : identique au planning -> enregistrée ; écart -> soumis à validation """
    if not utils_espace_collaborateur.Get_parametres().get("collaborateurs_saisie_realise", False):
        return JsonResponse({"erreur": "La déclaration des heures n'est pas ouverte"}, status=403)
    collaborateur = request.user.collaborateur
    aujourdhui = datetime.date.today()
    limite = aujourdhui - datetime.timedelta(days=aujourdhui.weekday() + 7)
    try:
        lignes = json.loads(request.POST.get("heures", "[]"))
    except ValueError:
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    if not isinstance(lignes, list) or not all(isinstance(ligne, dict) for ligne in lignes):
        return JsonResponse({"erreur": "Données incorrectes"}, status=400)
    lignes = lignes[:200]
    enregistrees, ecarts = 0, 0
    with transaction.atomic():
        for ligne in lignes:
            evenement = EvenementCollaborateur.objects.select_for_update().filter(pk=ligne.get("id") or 0, collaborateur=collaborateur, type_evenement__type="ADDITION",
                                                                                  date_debut__date__gte=limite, date_debut__date__lte=aujourdhui).first()
            if not evenement:
                continue
            try:
                debut = Lire_heure_jour(str(ligne.get("rd", "")), evenement.date_debut.date())
                fin = Lire_heure_jour(str(ligne.get("rf", "")), evenement.date_debut.date())
            except ValueError:
                return JsonResponse({"erreur": "Horaire incorrect le %s" % evenement.date_debut.strftime("%d/%m")}, status=400)
            if fin <= debut:
                fin += datetime.timedelta(days=1)
            if (debut, fin) == (evenement.realise_debut, evenement.realise_fin) and not evenement.declare_etat:
                continue
            if (debut, fin) == (evenement.declare_debut, evenement.declare_fin) and evenement.declare_etat == "ATTENTE":
                continue
            if (debut, fin) == (evenement.date_debut, evenement.date_fin):
                evenement.realise_debut, evenement.realise_fin = debut, fin
                evenement.declare_debut = evenement.declare_fin = evenement.declare_etat = None
                evenement.version += 1
                enregistrees += 1
            else:
                evenement.declare_debut, evenement.declare_fin, evenement.declare_etat = debut, fin, "ATTENTE"
                ecarts += 1
            evenement.declare_date = datetime.datetime.now()
            evenement.save()
    if ecarts:
        utils_espace_collaborateur.Notifier_a_verifier(collaborateur, "Heures déclarées à valider pour %s" % collaborateur.Get_nom(),
                                                       "a déclaré %d horaire%s différent%s du planning." % (ecarts, "s" if ecarts > 1 else "", "s" if ecarts > 1 else ""),
                                                       "menu Collaborateurs > Heures déclarées", request=request)
    message = "Aucune modification"
    if enregistrees or ecarts:
        message = " ; ".join(texte for texte in [
            "%d horaire%s enregistré%s" % (enregistrees, "s" if enregistrees > 1 else "", "s" if enregistrees > 1 else "") if enregistrees else "",
            "%d écart%s transmis à votre responsable" % (ecarts, "s" if ecarts > 1 else "") if ecarts else ""] if texte)
    messages.add_message(request, messages.SUCCESS, message)
    return JsonResponse({"succes": True})
