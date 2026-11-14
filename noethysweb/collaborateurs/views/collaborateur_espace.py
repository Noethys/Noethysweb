# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, html, datetime
from django.urls import reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.db.models import Q
from django.views.generic.edit import UpdateView
from core.models import Collaborateur, Utilisateur, Mail, Destinataire
from collaborateurs.views.collaborateur import Onglet
from collaborateurs.forms.collaborateur_espace import Formulaire
from collaborateurs.utils import utils_espace_collaborateur


def Get_collaborateur(request):
    """ Collaborateur demandé, uniquement s'il est accessible à l'utilisateur (superviseur de l'un de ses groupes ou groupe sans superviseur) """
    if not request.user.has_perm("core.collaborateur_identite"):
        return None
    return Collaborateur.objects.filter((Q(groupes__superviseurs=request.user) | Q(groupes__superviseurs__isnull=True)), pk=request.POST.get("idcollaborateur") or 0).distinct().first()


class Consulter(Onglet, UpdateView):
    """ Accès du collaborateur à son espace du portail (codes d'accès, activation, notifications) """
    template_name = "collaborateurs/collaborateur_espace.html"
    mode = "CONSULTATION"
    model = Collaborateur
    form_class = Formulaire

    def test_func_page(self):
        return self.request.user.has_perm("core.collaborateur_identite") and super(Consulter, self).test_func_page()

    def get_object(self):
        return Collaborateur.objects.select_related("utilisateur").get(pk=self.kwargs["idcollaborateur"])

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Consulter, self).get_form_kwargs(**kwargs)
        form_kwargs.update({"idcollaborateur": self.kwargs["idcollaborateur"], "request": self.request, "mode": self.mode})
        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context["onglet_actif"] = "espace"
        context["box_titre"] = "Espace collaborateur"
        context["box_introduction"] = "L'espace collaborateur du portail permet au collaborateur de consulter son planning, ses congés et ses documents, de demander une absence, de transmettre une pièce et de déclarer ses heures réalisées. Gérez ici son accès et ses identifiants de connexion."
        if not utils_espace_collaborateur.Espace_actif():
            context["box_introduction"] += " <b class='text-danger'>L'espace collaborateur est actuellement désactivé : activez-le dans Paramétrage > Paramètres du portail > Espace collaborateur.</b>"
        collaborateur = self.get_object()
        context["sans_compte"] = not collaborateur.utilisateur_id
        context["sans_email"] = not utils_espace_collaborateur.Adresse_collaborateur(collaborateur)
        return context

    def get(self, request, *args, **kwargs):
        # Création automatique des codes d'accès à la première consultation (comme pour les familles)
        collaborateur = self.get_object()
        if not collaborateur.utilisateur_id:
            utils_espace_collaborateur.Creer_compte(collaborateur)
        return super(Consulter, self).get(request, *args, **kwargs)


class Modifier(Consulter):
    mode = "EDITION"

    def post(self, request, *args, **kwargs):
        collaborateur = self.get_object()
        form = Formulaire(request.POST, instance=collaborateur, idcollaborateur=collaborateur.pk, request=request, mode=self.mode)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        if not collaborateur.utilisateur_id:
            utils_espace_collaborateur.Creer_compte(collaborateur)
            collaborateur.refresh_from_db()
        utilisateur = collaborateur.utilisateur

        identifiant = (form.cleaned_data.get("internet_identifiant") or "").strip()
        if identifiant and identifiant != utilisateur.username:
            if Utilisateur.objects.filter(username__iexact=identifiant).exclude(pk=utilisateur.pk).exists():
                messages.add_message(request, messages.ERROR, "Cet identifiant est déjà attribué à un autre compte !")
                return self.render_to_response(self.get_context_data(form=form))
            utilisateur.username = identifiant
            collaborateur.internet_identifiant = identifiant

        mdp = form.cleaned_data.get("internet_mdp")
        if mdp and mdp != "*****" and mdp != Collaborateur.objects.get(pk=collaborateur.pk).internet_mdp:
            # Nouveau mot de passe provisoire : à personnaliser lors de la prochaine connexion
            utilisateur.set_password(mdp)
            utilisateur.force_reset_password = True
            utilisateur.date_expiration_mdp = form.cleaned_data.get("date_expiration_mdp")
            collaborateur.internet_mdp = mdp

        collaborateur.internet_actif = form.cleaned_data.get("internet_actif")
        collaborateur.notifier_planning = form.cleaned_data.get("notifier_planning")
        utilisateur.is_active = collaborateur.internet_actif
        utilisateur.save()
        collaborateur.save()
        return HttpResponseRedirect(reverse("collaborateur_espace", kwargs={"idcollaborateur": collaborateur.pk}))


def Regenerer_identifiant(request):
    collaborateur = Get_collaborateur(request)
    if not collaborateur:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    return JsonResponse({"identifiant": utils_espace_collaborateur.Creation_identifiant(collaborateur)})


def Regenerer_mdp(request):
    if not Get_collaborateur(request):
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    from fiche_famille.utils.utils_internet import CreationMDP
    mdp, date_expiration_mdp = CreationMDP()
    return JsonResponse({"mdp": mdp, "date_expiration_mdp": str(date_expiration_mdp)})


def Envoyer_codes(request):
    """ Prépare un email avec les codes d'accès et ouvre l'éditeur d'emails """
    collaborateur = Get_collaborateur(request)
    if not collaborateur or not collaborateur.utilisateur_id:
        return JsonResponse({"erreur": "Collaborateur introuvable"}, status=404)
    adresse = utils_espace_collaborateur.Adresse_collaborateur(collaborateur)
    if not adresse:
        return JsonResponse({"erreur": "Ce collaborateur n'a pas d'adresse email (fiche collaborateur > Coordonnées)"}, status=400)
    if not collaborateur.internet_mdp or collaborateur.internet_mdp == "*****":
        return JsonResponse({"erreur": "Le mot de passe a été personnalisé par le collaborateur. Générez un nouveau mot de passe provisoire pour pouvoir l'envoyer."}, status=400)
    utilisateur = collaborateur.utilisateur
    if utilisateur.date_expiration_mdp and utilisateur.date_expiration_mdp < datetime.datetime.now():
        return JsonResponse({"erreur": "Le mot de passe a expiré. Vous devez en générer un nouveau."}, status=400)
    url_portail = request.build_absolute_uri(reverse("portail_connexion"))
    texte = "".join("<p>%s</p>" % ligne for ligne in [
        "Bonjour %s," % html.escape(collaborateur.prenom or collaborateur.nom),
        "Votre espace collaborateur vous permet de consulter votre planning, vos congés et vos documents.",
        "Adresse : <a href='%s'>%s</a><br>Identifiant : <b>%s</b><br>Mot de passe provisoire : <b>%s</b>%s" % (
            url_portail, url_portail, html.escape(utilisateur.username), html.escape(collaborateur.internet_mdp),
            "<br>(valable jusqu'au %s)" % utilisateur.date_expiration_mdp.strftime("%d/%m/%Y") if utilisateur.date_expiration_mdp else ""),
        "Vous devrez choisir un mot de passe personnel lors de votre première connexion.", "Cordialement."])
    mail = Mail.objects.create(categorie="saisie_libre", objet="Vos codes d'accès à l'espace collaborateur", html=texte, adresse_exp=request.user.Get_adresse_exp_defaut(),
                               selection="NON_ENVOYE", verrouillage_destinataires=True, utilisateur=request.user)
    destinataire = Destinataire.objects.create(categorie="collaborateur", collaborateur=collaborateur, adresse=adresse, valeurs=json.dumps({}))
    mail.destinataires.add(destinataire)
    return JsonResponse({"url": reverse("editeur_emails", kwargs={"pk": mail.pk})})
