# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, logging
logger = logging.getLogger(__name__)
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Q, Exists, OuterRef
from core.views.base import CustomView
from core.models import ContratCollaborateur, ModeleEmail, Mail, Destinataire
from core.utils import utils_texte
from collaborateurs.forms.pieces_manquantes import Formulaire, CHOIX_ETATS
from collaborateurs.utils import utils_pieces_manquantes
from collaborateurs.utils.utils_collaborateur import Condition_contrat_en_cours, Situation_contrat
from collaborateurs.views.planning_individuel import Collaborateurs_accessibles

PERMISSION = "core.pieces_manquantes_collaborateurs"
CATEGORIE_EMAIL = "rappel_pieces_collaborateurs"
ETATS_RELANCE = ("ABSENTE", "EXPIREE", "BIENTOT", "REFUSEE")     # Les pièces transmises en attente de vérification ne sont pas réclamées
CLASSES_ETATS = {"ABSENTE": "danger", "EXPIREE": "danger", "REFUSEE": "warning", "BIENTOT": "info", "ATTENTE": "secondary"}
EMAIL_DEFAUT = "<p>Bonjour {COLLABORATEUR_PRENOM},</p><p>Afin de compléter votre dossier, merci de nous transmettre les pièces suivantes : {LISTE_PIECES_MANQUANTES}.</p>" \
               "<p>Vous pouvez les déposer depuis votre espace collaborateur ou les remettre à votre responsable.</p><p>Cordialement.</p>"


def Get_collaborateurs(user=None, parametres={}):
    """ Collaborateurs concernés par les paramètres (et accessibles à l'utilisateur) """
    date_reference = parametres["date"]
    collaborateurs = Collaborateurs_accessibles(user)
    if parametres.get("groupes"):
        collaborateurs = collaborateurs.filter(groupes__in=parametres["groupes"])
    if parametres["situation"] == "en_poste":
        collaborateurs = collaborateurs.filter(Exists(ContratCollaborateur.objects.filter(Condition_contrat_en_cours(date=date_reference, prefixe=""), collaborateur=OuterRef("pk"))))
    elif parametres["situation"] == "a_venir":
        collaborateurs = collaborateurs.filter(Exists(ContratCollaborateur.objects.filter(Q(date_fin__isnull=True) | Q(date_fin__gte=date_reference), collaborateur=OuterRef("pk"))))
    return list(collaborateurs.distinct().order_by("nom", "prenom"))


def Get_resultats(user=None, parametres={}):
    """ Lignes du tableau : une ligne par collaborateur ayant au moins une pièce dans les états demandés """
    collaborateurs = Get_collaborateurs(user, parametres)
    pieces = utils_pieces_manquantes.Get_liste_pieces_manquantes(collaborateurs=collaborateurs, date_reference=parametres["date"],
                                                                  delai_expiration=parametres.get("delai_expiration") or 0)
    contrats = {}
    for contrat in ContratCollaborateur.objects.select_related("type_poste").filter(collaborateur__in=collaborateurs):
        contrats.setdefault(contrat.collaborateur_id, []).append(contrat)

    etats = set(parametres["etats"])
    lignes, totaux = [], {etat: 0 for etat, label in CHOIX_ETATS}
    for collaborateur in collaborateurs:
        liste = [piece for piece in pieces.get(collaborateur.pk, []) if piece["etat"] in etats]
        if not liste:
            continue
        for piece in liste:
            piece["classe"] = CLASSES_ETATS[piece["etat"]]
            piece["label_etat"] = utils_pieces_manquantes.LABELS_ETATS[piece["etat"]]
            totaux[piece["etat"]] += 1
        situation = Situation_contrat(contrats.get(collaborateur.pk, []), parametres["date"])
        lignes.append({
            "collaborateur": collaborateur,
            "poste": situation["contrat"].type_poste.nom if situation["contrat"] else "",
            "adresse": collaborateur.travail_mail or collaborateur.mail or "",
            "pieces": liste,
            "a_relancer": len([piece for piece in liste if piece["etat"] in ETATS_RELANCE]),
        })
    return {"lignes": lignes, "nbre_collaborateurs": len(collaborateurs), "nbre_pieces": sum(totaux.values()),
            "totaux": [{"code": etat, "label": label, "nbre": totaux[etat], "classe": CLASSES_ETATS[etat]} for etat, label in CHOIX_ETATS if etat in etats]}


def Envoyer_emails(request):
    """ Prépare un email de rappel pour les collaborateurs cochés et ouvre l'éditeur d'emails """
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation d'accéder à cette fonctionnalité"}, status=403)
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Les paramètres sont incorrects. Cliquez sur Actualiser puis réessayez."}, status=400)
    try:
        ids = {int(idcollaborateur) for idcollaborateur in json.loads(request.POST.get("collaborateurs", "[]"))}
    except (TypeError, ValueError):
        ids = set()
    if not ids:
        return JsonResponse({"erreur": "Cochez au moins un collaborateur dans la liste"}, status=400)

    # Les pièces sont recalculées côté serveur : seules les pièces non fournies, expirées, refusées ou expirant bientôt sont réclamées
    lignes = [ligne for ligne in Get_resultats(request.user, form.cleaned_data)["lignes"] if ligne["collaborateur"].pk in ids and ligne["a_relancer"]]
    if not lignes:
        return JsonResponse({"erreur": "Aucune pièce à réclamer pour les collaborateurs cochés (les pièces transmises à vérifier ne sont pas réclamées)"}, status=400)

    modele_email = ModeleEmail.objects.filter(categorie=CATEGORIE_EMAIL, defaut=True).first()
    mail = Mail.objects.create(
        categorie=CATEGORIE_EMAIL,
        objet=modele_email.objet if modele_email else "Pièces à fournir pour votre dossier",
        html=modele_email.html if modele_email else EMAIL_DEFAUT,
        adresse_exp=request.user.Get_adresse_exp_defaut(),
        selection="NON_ENVOYE",
        verrouillage_destinataires=True,
        utilisateur=request.user,
    )

    sans_adresse = []
    for ligne in lignes:
        collaborateur = ligne["collaborateur"]
        if not ligne["adresse"]:
            sans_adresse.append(collaborateur.Get_nom())
            continue
        texte = utils_texte.Convert_liste_to_texte_virgules([piece["texte"] for piece in ligne["pieces"] if piece["etat"] in ETATS_RELANCE])
        valeurs = {"{COLLABORATEUR_CIVILITE}": collaborateur.get_civilite_display(), "{COLLABORATEUR_NOM}": collaborateur.nom,
                   "{COLLABORATEUR_PRENOM}": collaborateur.prenom or "", "{LISTE_PIECES_MANQUANTES}": texte}
        destinataire = Destinataire.objects.create(categorie="collaborateur", collaborateur=collaborateur, adresse=ligne["adresse"], valeurs=json.dumps(valeurs))
        mail.destinataires.add(destinataire)

    if sans_adresse and not mail.destinataires.exists():
        mail.delete()
        return JsonResponse({"erreur": "Aucun des collaborateurs cochés n'a d'adresse email : %s" % ", ".join(sans_adresse)}, status=400)
    if sans_adresse:
        messages.add_message(request, messages.ERROR, "Adresses email manquantes : %s" % ", ".join(sans_adresse))
    return JsonResponse({"url": reverse("editeur_emails", kwargs={"pk": mail.pk})})


class View(CustomView, TemplateView):
    menu_code = "pieces_manquantes_collaborateurs"
    template_name = "collaborateurs/pieces_manquantes.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Pièces manquantes des collaborateurs"
        context["box_introduction"] = "Retrouvez ici les pièces exigées des collaborateurs (pièces obligatoires ou liées à leurs qualifications et à leurs postes) qui n'ont pas été fournies, " \
                                      "ne sont plus valables ou arrivent à expiration. Cochez des collaborateurs puis cliquez sur <b>Envoyer des rappels par email</b> pour leur réclamer les pièces."
        if "form_parametres" not in kwargs:
            form = Formulaire(request=self.request)
            context["form_parametres"] = form
            parametres = {nom: champ.initial for nom, champ in form.fields.items()}
            parametres["groupes"] = []
            context["resultats"] = Get_resultats(self.request.user, parametres)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, resultats=Get_resultats(request.user, form.cleaned_data)))
