# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, json, decimal
from django.http import JsonResponse, HttpResponseForbidden
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.db import transaction
from core.views.base import CustomView
from core.models import Collaborateur, GroupeCollaborateurs, TypeCongeCollaborateur, DroitCongeCollaborateur, DemandeAbsenceCollaborateur
from collaborateurs.utils import utils_conges, utils_planning
from collaborateurs.utils.utils_planning import Parse_date
from collaborateurs.views.collaborateur import Onglet
from collaborateurs.views.planning_individuel import Collaborateurs_accessibles


def Verifie_permission(function):
    def _function(request, *args, **kwargs):
        if not utils_conges.Peut_acceder(request.user):
            return HttpResponseForbidden()
        return function(request, *args, **kwargs)
    return _function


def Erreur(texte="", status=400):
    return JsonResponse({"erreur": texte}, status=status)


def Get_demande(request):
    """ Demande accessible à l'utilisateur """
    try:
        iddemande = int(request.POST.get("iddemande", 0))
    except (TypeError, ValueError):
        return None
    return DemandeAbsenceCollaborateur.objects.select_related("type_conge__categorie", "collaborateur", "auteur", "decideur").filter(
        pk=iddemande, collaborateur__in=Collaborateurs_accessibles(request.user)).first()


def Get_int(request, nom=""):
    try:
        return int(request.POST.get(nom) or 0)
    except (TypeError, ValueError):
        return 0


def Lire_demande(request, demande=None):
    """ Remplit une demande avec les champs du formulaire """
    demande = demande or DemandeAbsenceCollaborateur()
    collaborateur = Collaborateurs_accessibles(request.user).filter(pk=Get_int(request, "idcollaborateur")).first()
    type_conge = TypeCongeCollaborateur.objects.select_related("categorie").filter(pk=Get_int(request, "idtype")).first()
    if not collaborateur:
        raise utils_conges.Erreur("Sélectionnez un collaborateur")
    if not type_conge:
        raise utils_conges.Erreur("Sélectionnez un type de congé")
    demande.collaborateur, demande.type_conge = collaborateur, type_conge
    try:
        demande.date_debut = Parse_date(request.POST.get("date_debut"))
        demande.date_fin = Parse_date(request.POST.get("date_fin")) or demande.date_debut
        demande.heure_debut = utils_conges.Heure(request.POST["heure_debut"]) if request.POST.get("heure_debut") else None
        demande.heure_fin = utils_conges.Heure(request.POST["heure_fin"]) if request.POST.get("heure_fin") else None
    except ValueError:
        raise utils_conges.Erreur("Les dates ou les heures saisies sont incorrectes")
    demande.debut_apres_midi = request.POST.get("debut_apres_midi") == "true" and not demande.heure_debut
    demande.fin_matin = request.POST.get("fin_matin") == "true" and not demande.heure_debut
    demande.motif = request.POST.get("motif", "").strip() or None
    return demande


# ------------------------------------------------- Demandes -------------------------------------------------

@Verifie_permission
def Get_demandes(request):
    etat = request.POST.get("etat", "ATTENTE")
    demandes = DemandeAbsenceCollaborateur.objects.select_related("type_conge__categorie", "collaborateur", "auteur", "decideur").filter(collaborateur__in=Collaborateurs_accessibles(request.user))
    if Get_int(request, "idcollaborateur"):
        demandes = demandes.filter(collaborateur_id=Get_int(request, "idcollaborateur"))
    nb_attente = demandes.filter(etat="ATTENTE").count()
    if etat in ("ATTENTE", "VALIDEE", "REFUSEE", "ANNULEE"):
        demandes = demandes.filter(etat=etat)
    demandes = demandes.order_by("date_debut", "collaborateur__nom") if etat == "ATTENTE" else demandes.order_by("-date_debut", "collaborateur__nom")
    ids_modifiables = utils_planning.Get_ids_modifiables(request.user)
    return JsonResponse({"demandes": [utils_conges.Serialiser_demande(demande, ids_modifiables=ids_modifiables) for demande in demandes[:500]], "nb_attente": nb_attente})


@Verifie_permission
def Calculer(request):
    """ Durée d'une demande en cours de saisie et effet sur le solde """
    try:
        demande = Lire_demande(request)
        calcul = utils_conges.Calculer_demande(demande, utils_conges.Get_journee(request.user))
    except utils_conges.Erreur as erreur:
        return JsonResponse({"erreur": str(erreur)})
    compteur = utils_conges.Get_compteurs([demande.collaborateur.pk], [demande.type_conge], annee=utils_conges.Annee_de(demande.type_conge, demande.date_debut))[(demande.collaborateur.pk, demande.type_conge.pk)]
    if Get_int(request, "iddemande"):
        ancienne = DemandeAbsenceCollaborateur.objects.filter(pk=Get_int(request, "iddemande"), etat="ATTENTE", type_conge=demande.type_conge).first()
        if ancienne:
            compteur["attente"] -= float(ancienne.quantite)
    apres = compteur["solde"] - compteur["attente"] - float(calcul["quantite"])
    return JsonResponse({"quantite_txt": utils_conges.Format_valeur(calcul["quantite"], demande.type_conge.unite), "periode": compteur["periode"],
                         "solde_txt": compteur["solde_txt"], "attente_txt": utils_conges.Format_valeur(compteur["attente"], demande.type_conge.unite) if compteur["attente"] else "",
                         "apres_txt": utils_conges.Format_valeur(apres, demande.type_conge.unite), "negatif": apres < -0.001,
                         "bloquant": apres < -0.001 and not demande.type_conge.solde_negatif})


@Verifie_permission
def Enregistrer_demande(request):
    """ Création ou modification d'une demande en attente """
    ancienne = None
    if Get_int(request, "iddemande"):
        ancienne = Get_demande(request)
        if not ancienne or ancienne.etat != "ATTENTE":
            return Erreur("Seule une demande en attente peut être modifiée")
    try:
        demande = Lire_demande(request, ancienne)
        if demande.type_conge.pk and not demande.type_conge.actif and not ancienne:
            raise utils_conges.Erreur("Ce type de congé n'est plus actif")
        demande.quantite = utils_conges.Calculer_demande(demande, utils_conges.Get_journee(request.user))["quantite"]
    except utils_conges.Erreur as erreur:
        return Erreur(str(erreur))
    if not ancienne:
        demande.auteur = request.user
    demande.save()
    utils_conges.Historique(demande, request.user, "Modification d'une demande d'absence" if ancienne else "Saisie d'une demande d'absence")
    return JsonResponse({"demande": utils_conges.Serialiser_demande(demande, user=request.user)})


@Verifie_permission
def Apercu(request):
    demande = Get_demande(request)
    if not demande:
        return Erreur("Demande introuvable", 404)
    try:
        apercu = utils_conges.Apercu(demande, request.user) if demande.etat == "ATTENTE" else None
    except utils_conges.Erreur as erreur:
        apercu = {"erreurs": [str(erreur)]}
    return JsonResponse({"demande": utils_conges.Serialiser_demande(demande, user=request.user), "apercu": apercu})


@Verifie_permission
def Decider(request):
    demande = Get_demande(request)
    if not demande:
        return Erreur("Demande introuvable", 404)
    if not utils_conges.Peut_traiter(request.user, demande.collaborateur_id):
        return Erreur("Vous n'avez pas l'autorisation de traiter les demandes de ce collaborateur", 403)
    commentaire = request.POST.get("commentaire", "").strip()
    try:
        if request.POST.get("decision") == "valider":
            resultat = utils_conges.Valider(demande, request.user, commentaire)
            message = "Demande validée : %d évènement%s d'absence créé%s" % (resultat["crees"], "s" if resultat["crees"] > 1 else "", "s" if resultat["crees"] > 1 else "")
            if resultat["retires"]:
                message += ", %d évènement%s de travail retiré%s" % (resultat["retires"], "s" if resultat["retires"] > 1 else "", "s" if resultat["retires"] > 1 else "")
        else:
            utils_conges.Refuser(demande, request.user, commentaire)
            message = "Demande refusée"
    except utils_conges.Erreur as erreur:
        return Erreur(str(erreur), 409)
    return JsonResponse({"message": message})


@Verifie_permission
def Annuler(request):
    demande = Get_demande(request)
    if not demande:
        return Erreur("Demande introuvable", 404)
    if not utils_conges.Peut_traiter(request.user, demande.collaborateur_id) and not (demande.etat == "ATTENTE" and demande.auteur_id == request.user.pk):
        return Erreur("Vous n'avez pas l'autorisation d'annuler cette demande", 403)
    try:
        resultat = utils_conges.Annuler(demande, request.user, restaurer=request.POST.get("restaurer") == "true", commentaire=request.POST.get("commentaire", "").strip())
    except utils_conges.Erreur as erreur:
        return Erreur(str(erreur), 409)
    message = "Demande annulée"
    if resultat["restaures"]:
        message += " : %d évènement%s de travail restauré%s" % (resultat["restaures"], "s" if resultat["restaures"] > 1 else "", "s" if resultat["restaures"] > 1 else "")
    if resultat["ignores"]:
        message += " (%d non restauré%s car le créneau est déjà occupé)" % (resultat["ignores"], "s" if resultat["ignores"] > 1 else "")
    return JsonResponse({"message": message})


# ------------------------------------------------- Compteurs et droits -------------------------------------------------

@Verifie_permission
def Get_compteurs(request):
    """ Compteurs d'un type de congé pour tous les collaborateurs accessibles, ou de tous les types pour un collaborateur """
    accessibles = Collaborateurs_accessibles(request.user)
    ids_modifiables = utils_planning.Get_ids_modifiables(request.user)
    annee = Get_int(request, "annee") or None
    if Get_int(request, "idcollaborateur"):
        collaborateur = accessibles.filter(pk=Get_int(request, "idcollaborateur")).first()
        if not collaborateur:
            return Erreur("Collaborateur introuvable", 404)
        types = list(TypeCongeCollaborateur.objects.select_related("categorie").order_by("ordre", "nom"))
        compteurs = utils_conges.Get_compteurs([collaborateur.pk], types, annee=annee)
        lignes = [dict(compteurs[(collaborateur.pk, type_conge.pk)], actif=type_conge.actif, droits_detail=[
            {"id": droit.pk, "nature": droit.get_nature_display(), "valeur_txt": utils_conges.Format_valeur(droit.valeur, type_conge.unite), "motif": droit.motif or "",
             "date": droit.date_saisie.strftime("%d/%m/%Y")}
            for droit in DroitCongeCollaborateur.objects.filter(collaborateur=collaborateur, type_conge=type_conge, annee=compteurs[(collaborateur.pk, type_conge.pk)]["annee"]).order_by("pk")])
            for type_conge in types if type_conge.actif or compteurs[(collaborateur.pk, type_conge.pk)]["droits"] or compteurs[(collaborateur.pk, type_conge.pk)]["poses"]]
        return JsonResponse({"lignes": lignes, "modifiable": collaborateur.pk in ids_modifiables})

    type_conge = TypeCongeCollaborateur.objects.select_related("categorie").filter(pk=Get_int(request, "idtype")).first()
    if not type_conge:
        return JsonResponse({"lignes": []})
    collaborateurs = list(accessibles)
    if Get_int(request, "idgroupe"):
        collaborateurs = [collaborateur for collaborateur in collaborateurs if collaborateur.groupes.filter(pk=Get_int(request, "idgroupe")).exists()]
    compteurs = utils_conges.Get_compteurs([collaborateur.pk for collaborateur in collaborateurs], [type_conge], annee=annee)
    lignes = [dict(compteurs[(collaborateur.pk, type_conge.pk)], c=collaborateur.pk, collaborateur=collaborateur.Get_nom(), modifiable=collaborateur.pk in ids_modifiables)
              for collaborateur in collaborateurs]
    periode = utils_conges.Periode(type_conge, annee or utils_conges.Annee_de(type_conge, datetime.date.today()))
    return JsonResponse({"lignes": lignes, "periode": periode["libelle"], "annee": periode["annee"], "unite": type_conge.unite})


@Verifie_permission
def Enregistrer_droits(request):
    """ Attribution de droits à un ou plusieurs collaborateurs """
    type_conge = TypeCongeCollaborateur.objects.filter(pk=Get_int(request, "idtype")).first()
    if not type_conge:
        return Erreur("Sélectionnez un type de congé")
    annee = Get_int(request, "annee")
    if not 1900 < annee < 2200:
        return Erreur("Sélectionnez une période")
    try:
        valeur = decimal.Decimal(request.POST.get("valeur", "").replace(",", ".").strip())
        ids = [int(valeur_id) for valeur_id in json.loads(request.POST.get("collaborateurs", "[]"))]
    except (decimal.InvalidOperation, ValueError, TypeError):
        return Erreur("Saisissez une valeur numérique (exemple : 25 ou 2,5)")
    if not valeur:
        return Erreur("Saisissez une valeur différente de zéro")
    nature = request.POST.get("nature") if request.POST.get("nature") in ("DROIT", "REPORT", "AJUSTEMENT") else "DROIT"
    ids_modifiables = utils_planning.Get_ids_modifiables(request.user)
    collaborateurs = [collaborateur for collaborateur in Collaborateurs_accessibles(request.user).filter(pk__in=ids) if collaborateur.pk in ids_modifiables]
    if not collaborateurs:
        return Erreur("Sélectionnez au moins un collaborateur dont vous pouvez gérer les congés")
    motif = request.POST.get("motif", "").strip() or None
    with transaction.atomic():
        for collaborateur in collaborateurs:
            DroitCongeCollaborateur.objects.create(collaborateur=collaborateur, type_conge=type_conge, annee=annee, valeur=valeur, nature=nature, motif=motif, utilisateur=request.user)
    return JsonResponse({"message": "Droits enregistrés pour %d collaborateur%s" % (len(collaborateurs), "s" if len(collaborateurs) > 1 else "")})


@Verifie_permission
def Supprimer_droit(request):
    droit = DroitCongeCollaborateur.objects.filter(pk=Get_int(request, "iddroit"), collaborateur__in=Collaborateurs_accessibles(request.user)).first()
    if not droit or not utils_conges.Peut_traiter(request.user, droit.collaborateur_id):
        return Erreur("Droit introuvable ou non modifiable", 403)
    droit.delete()
    return JsonResponse({"succes": True})


# ------------------------------------------------- Pages -------------------------------------------------

class Contexte_conges():
    def Get_contexte_conges(self, mode="demandes", collaborateur=None):
        user = self.request.user
        accessibles = Collaborateurs_accessibles(user)
        groupes = []
        for groupe in GroupeCollaborateurs.objects.prefetch_related("collaborateur_groupes").order_by("nom"):
            groupes.append({"id": groupe.pk, "nom": groupe.nom, "collaborateurs": [collaborateur.pk for collaborateur in groupe.collaborateur_groupes.all()]})
        aujourdhui = datetime.date.today()
        types = [{"id": type_conge.pk, "nom": type_conge.nom, "unite": type_conge.unite, "actif": type_conge.actif, "mois_debut": type_conge.mois_debut,
                  "annee": utils_conges.Annee_de(type_conge, aujourdhui)} for type_conge in TypeCongeCollaborateur.objects.order_by("ordre", "nom")]
        ids_modifiables = utils_planning.Get_ids_modifiables(user)
        return {"conges_config": {
            "mode": mode, "idcollaborateur": collaborateur.pk if collaborateur else 0, "types": types, "groupes": groupes,
            "collaborateurs": [{"id": c.pk, "nom": c.Get_nom(), "modifiable": c.pk in ids_modifiables} for c in accessibles],
            "aujourdhui": str(aujourdhui),
        }}


class View_demandes(CustomView, TemplateView, Contexte_conges):
    menu_code = "demandes_absences_collaborateurs"
    template_name = "collaborateurs/conges_demandes.html"

    def get_context_data(self, **kwargs):
        context = super(View_demandes, self).get_context_data(**kwargs)
        context["page_titre"] = "Demandes d'absence"
        context.update(self.Get_contexte_conges(mode="demandes"))
        return context


class View_compteurs(CustomView, TemplateView, Contexte_conges):
    menu_code = "compteurs_conges_collaborateurs"
    template_name = "collaborateurs/conges_compteurs.html"

    def get_context_data(self, **kwargs):
        context = super(View_compteurs, self).get_context_data(**kwargs)
        context["page_titre"] = "Compteurs de congés"
        context.update(self.Get_contexte_conges(mode="compteurs"))
        return context


class Onglet_conges(Onglet, DetailView, Contexte_conges):
    template_name = "collaborateurs/collaborateur_conges.html"

    def test_func_page(self):
        return super(Onglet_conges, self).test_func_page() and utils_conges.Peut_acceder(self.request.user)

    def get_context_data(self, **kwargs):
        context = super(Onglet_conges, self).get_context_data(**kwargs)
        context["onglet_actif"] = "conges"
        context["box_titre"] = "Congés et absences"
        context.update(self.Get_contexte_conges(mode="fiche", collaborateur=self.object))
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs["idcollaborateur"])
