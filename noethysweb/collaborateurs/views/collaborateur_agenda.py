# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import JsonResponse
from django.views.generic import TemplateView
from core.models import Collaborateur, AffectationCollaborateur
from collaborateurs.views.collaborateur import Onglet
from collaborateurs.utils import utils_agenda_ical, utils_planning, utils_espace_collaborateur
from collaborateurs.utils.utils_affectations import Arbre


def Peut_gerer(user=None):
    """ Mêmes droits que le planning des collaborateurs (individuel ou général) """
    from collaborateurs.views.planning_individuel import Peut_acceder
    return Peut_acceder(user)


def Get_adresses(collaborateur=None):
    """ Adresses email possibles pour l'envoi du lien : (code, libellé, adresse) """
    adresses = []
    if collaborateur.travail_mail:
        adresses.append(("pro", "Email professionnel", collaborateur.travail_mail))
    if collaborateur.mail and collaborateur.mail != collaborateur.travail_mail:
        adresses.append(("perso", "Email personnel", collaborateur.mail))
    return adresses


class Consulter(Onglet, TemplateView):
    template_name = "collaborateurs/collaborateur_agenda.html"

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        collaborateur = Collaborateur.objects.select_related("ical_affectation").get(pk=self.kwargs["idcollaborateur"])
        arbre = Arbre()
        context["onglet_actif"] = "agenda"
        context["box_titre"] = "Agenda iCal"
        context["box_introduction"] = ("Le lien iCal permet au collaborateur d'afficher son planning dans l'agenda de son téléphone ou de son ordinateur "
                                       "(Google Agenda, Outlook, iPhone...). L'agenda est en lecture seule et se met à jour automatiquement. "
                                       "Il contient les évènements des 60 derniers jours et des 12 prochains mois.")
        context["collaborateur"] = collaborateur
        context["url_ical"] = utils_agenda_ical.Get_url(self.request, collaborateur)
        context["date_dernier_envoi"] = utils_agenda_ical.Get_date_dernier_envoi(collaborateur) if collaborateur.token_ical else None
        context["adresses"] = [{"code": code, "label": label, "adresse": adresse} for code, label, adresse in Get_adresses(collaborateur)]
        context["peut_modifier"] = collaborateur.pk in utils_planning.Get_ids_modifiables(self.request.user)
        # Affectations actives, plus l'affectation déjà choisie si elle a été désactivée
        context["choix_affectations"] = [{"id": affectation.pk, "nom": "   " * niveau + affectation.nom}
                                         for affectation, niveau in arbre.Parcourir() if affectation.actif or affectation.pk == collaborateur.ical_affectation_id]
        return context


def Action(request):
    """ Actions de la rubrique Agenda iCal : activer, régénérer, désactiver, enregistrer les paramètres, préparer l'email """
    if not Peut_gerer(request.user):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de gérer l'agenda de ce collaborateur"}, status=403)
    try:
        idcollaborateur = int(request.POST.get("idcollaborateur", 0))
    except (TypeError, ValueError):
        idcollaborateur = 0
    if idcollaborateur not in utils_planning.Get_ids_modifiables(request.user):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation de gérer l'agenda de ce collaborateur"}, status=403)
    collaborateur = Collaborateur.objects.filter(pk=idcollaborateur).first()
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)

    action = request.POST.get("action")

    if action in ("activer", "regenerer"):
        if action == "activer" and collaborateur.token_ical:
            return JsonResponse({"succes": True})
        utils_agenda_ical.Generer_jeton(collaborateur)
        return JsonResponse({"succes": True})

    if action == "desactiver":
        utils_agenda_ical.Desactiver(collaborateur)
        return JsonResponse({"succes": True})

    if action == "parametres":
        idaffectation = request.POST.get("affectation") or None
        if idaffectation:
            try:
                idaffectation = int(idaffectation)
            except (TypeError, ValueError):
                idaffectation = None
            if not idaffectation or not AffectationCollaborateur.objects.filter(pk=idaffectation).exists():
                return JsonResponse({"erreur": "Sélectionnez une affectation"}, status=400)
        collaborateur.ical_affectation_id = idaffectation
        collaborateur.ical_absences = request.POST.get("absences") == "1"
        collaborateur.ical_notes = request.POST.get("notes") == "1"
        collaborateur.ical_lieu = request.POST.get("lieu") == "1"
        collaborateur.save(update_fields=["ical_affectation", "ical_absences", "ical_notes", "ical_lieu"])
        return JsonResponse({"succes": True})

    if action == "envoyer":
        if not collaborateur.token_ical:
            return JsonResponse({"erreur": "Activez d'abord le lien iCal"}, status=400)
        adresses = {code: adresse for code, label, adresse in Get_adresses(collaborateur)}
        if not adresses:
            return JsonResponse({"erreur": "Ce collaborateur n'a pas d'adresse email (fiche collaborateur > Coordonnées)"}, status=400)
        adresse = adresses.get(request.POST.get("adresse")) or utils_espace_collaborateur.Adresse_collaborateur(collaborateur)
        return JsonResponse({"url": utils_agenda_ical.Preparer_email(request, collaborateur, adresse)})

    return JsonResponse({"erreur": "Action inconnue"}, status=400)
