# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Count
from django.contrib import messages
from core.views import crud
from core.models import ModeleEmail, Mail, PieceJointe, Destinataire, Famille, Individu, Collaborateur, Contact, SignatureEmail
from core.utils import utils_texte
from outils.forms.editeur_emails import Formulaire
from outils.utils import utils_email


def Get_modele_email(request):
    """ Renvoie le contenu HTML d'un modèle d'emails """
    idmodele = int(request.POST.get("idmodele"))
    modele = ModeleEmail.objects.filter(pk=idmodele).first()
    return JsonResponse({"objet": modele.objet, "html": modele.html})


def Get_signature_email(request):
    """ Renvoie le contenu HTML d'une signature d'emails """
    idsignature = int(request.POST.get("idsignature"))
    signature = SignatureEmail.objects.filter(pk=idsignature).first()
    return JsonResponse({"html": signature.html})


class Page(crud.Page):
    model = Mail
    menu_code = "editeur_emails"
    template_name = "outils/editeur_emails.html"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Editeur d'emails"
        context['afficher_menu_brothers'] = True
        context['categories'] = {} if not self.Get_idmail() else {item["categorie"]: item["nbre"] for item in Destinataire.objects.values('categorie').filter(mail=self.Get_idmail()).annotate(nbre=Count("pk"))}
        mail = Mail.objects.get(pk=self.Get_idmail()) if self.Get_idmail() else None
        categorie = mail.categorie if mail else "saisie_libre"
        context['modeles'] = ModeleEmail.objects.filter(categorie=categorie)
        context['signatures'] = SignatureEmail.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        context['mail'] = mail

        # Importe la liste des destinataires (Elimine les doublons)
        destinataires, adresses_temp = [], []
        nbre_envois_attente, nbre_envois_reussis, nbre_envois_echec = 0, 0, 0
        if self.Get_idmail():
            for destinataire in Destinataire.objects.select_related("famille", "individu", "contact", "collaborateur").prefetch_related("documents").filter(mail=self.Get_idmail()).order_by("adresse"):
                if True:#destinataire.adresse not in adresses_temp:
                    destinataires.append(destinataire)
                    adresses_temp.append(destinataire.adresse)
                    if not destinataire.resultat_envoi:
                        nbre_envois_attente += 1
                    elif destinataire.resultat_envoi == "ok":
                        nbre_envois_reussis += 1
                    else:
                        nbre_envois_echec += 1
        context['destinataires'] = destinataires
        context['nbre_envois_attente'] = nbre_envois_attente
        context['nbre_envois_echec'] = nbre_envois_echec
        context['nbre_envois_reussis'] = nbre_envois_reussis

        # Création du texte d'intro de la box Envois
        intro_envois = []
        if not destinataires: intro_envois.append("Aucun envoi")
        if nbre_envois_reussis: intro_envois.append("%d envois réussis" % nbre_envois_reussis) if nbre_envois_reussis > 1 else intro_envois.append("1 envoi réussi")
        if nbre_envois_attente: intro_envois.append("%d envois en attente" % nbre_envois_attente) if nbre_envois_attente > 1 else intro_envois.append("1 envoi en attente")
        if nbre_envois_echec: intro_envois.append("%d envois en échec" % nbre_envois_echec) if nbre_envois_echec > 1 else intro_envois.append("1 envoi en échec")
        context['intro_envoi'] = utils_texte.Convert_liste_to_texte_virgules(intro_envois)

        return context

    def Get_idmail(self):
        return self.kwargs.get('pk', None)

    def get_form_kwargs(self, **kwargs):
        """ Envoie l'idactivite au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idmail"] = self.Get_idmail()
        return form_kwargs

    def post(self, request, *args, **kwargs):
        # Validation du formulaire
        form = Formulaire(request.POST, request=self.request)
        if form.is_valid() == False:
            return self.render_to_response(self.get_context_data(form=form))

        idmail = self.kwargs.get("pk")

        # Modification du mail
        if idmail:
            mail = Mail.objects.get(pk=idmail)
            mail.objet = form.cleaned_data.get("objet")
            mail.html = form.cleaned_data.get("html")
            mail.adresse_exp = form.cleaned_data.get("adresse_exp")
            mail.selection = form.cleaned_data.get("selection")
            mail.save()

        # Création du mail
        if not idmail:
            mail = Mail.objects.create(
                categorie="saisie_libre",
                objet=form.cleaned_data.get("objet"),
                html=form.cleaned_data.get("html"),
                adresse_exp=form.cleaned_data.get("adresse_exp"),
                selection=form.cleaned_data.get("selection"),
                utilisateur=request.user,
            )
            messages.add_message(request, messages.INFO, "Un brouillon du mail a été enregistré")

        # Enregistrement d'une nouvelle pièce jointe
        piece = request.FILES.get('pieces_jointes')
        if piece:
            piece_jointe = PieceJointe.objects.create(nom=piece._name, fichier=piece)
            mail.pieces_jointes.add(piece_jointe)

        # Suppression d'une pièce
        suppr_piece_jointe = request.POST.get("suppr_piece_jointe")
        if suppr_piece_jointe:
            piece_jointe = PieceJointe.objects.get(pk=suppr_piece_jointe)
            piece_jointe.delete()

        # Redirection vers pages de sélection des destinataires
        action = request.POST.get("action")
        if action == "ajouter_familles": return HttpResponseRedirect(reverse_lazy("editeur_emails_familles", kwargs={"idmail": mail.pk}))
        if action == "ajouter_individus": return HttpResponseRedirect(reverse_lazy("editeur_emails_individus", kwargs={"idmail": mail.pk}))
        if action == "ajouter_collaborateurs": return HttpResponseRedirect(reverse_lazy("editeur_emails_collaborateurs", kwargs={"idmail": mail.pk}))
        if action == "ajouter_contacts": return HttpResponseRedirect(reverse_lazy("editeur_emails_contacts", kwargs={"idmail": mail.pk}))
        if action == "ajouter_diffusion": return HttpResponseRedirect(reverse_lazy("editeur_emails_listes_diffusion", kwargs={"idmail": mail.pk}))
        if action == "ajouter_saisie_libre": return HttpResponseRedirect(reverse_lazy("editeur_emails_saisie_libre", kwargs={"idmail": mail.pk}))

        # Envoyer
        if action == "envoyer":
            if not mail.destinataires:
                messages.add_message(request, messages.ERROR, "Vous devez sélectionner au moins un destinataire")
            elif not form.cleaned_data.get("adresse_exp"):
                messages.add_message(request, messages.ERROR, "Vous devez sélectionner une adresse d'expédition dans la liste")
            elif not form.cleaned_data.get("objet"):
                messages.add_message(request, messages.ERROR, "Vous devez saisir un objet")
            elif not form.cleaned_data.get("html"):
                messages.add_message(request, messages.ERROR, "Vous devez saisir un texte")
            else:
                utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)

        return HttpResponseRedirect(reverse_lazy("editeur_emails", kwargs={'pk': mail.pk}))


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire




# -------------------------------------------------------------------------------------------

class Page_destinataires(crud.Page):
    menu_code = "editeur_emails"

    def get_context_data(self, **kwargs):
        context = super(Page_destinataires, self).get_context_data(**kwargs)
        context['page_titre'] = "Editeur d'emails"
        context['idmail'] = self.kwargs.get("idmail")
        context['categorie'] = self.categorie
        return context

    def post(self, request, **kwargs):
        liste_selections = json.loads(request.POST.get("selections"))

        # Importe le mail
        mail = Mail.objects.get(pk=self.kwargs.get("idmail"))

        # Importe les adresses
        dict_adresses = {}
        if self.categorie == "famille":
            dict_adresses = {famille.pk: famille.mail for famille in Famille.objects.filter(email_blocage=False)}
        if self.categorie == "individu":
            dict_adresses = {individu.pk: individu.mail for individu in Individu.objects.all()}
        if self.categorie == "collaborateur":
            dict_adresses = {collaborateur.pk: collaborateur.mail for collaborateur in Collaborateur.objects.all()}
        if self.categorie == "contact":
            dict_adresses = {contact.pk: contact.mail for contact in Contact.objects.all()}

        # Importe la liste des destinataires actuels
        destinataires = Destinataire.objects.filter(categorie=self.categorie, mail=mail)
        liste_id = [getattr(destinataire, "%s_id" % self.categorie) for destinataire in destinataires]

        # Recherche le dernier ID de la table Destinataires
        dernier_destinataire = Destinataire.objects.last()
        idmax = dernier_destinataire.pk if dernier_destinataire else 0

        # Ajout des destinataires
        liste_ajouts = []
        for id in liste_selections:
            if id not in liste_id:
                adresse = dict_adresses.get(id, None)
                if adresse:
                    kwargs = {"{0}_id".format(self.categorie): id, "categorie": self.categorie, "adresse": adresse}
                    liste_ajouts.append(Destinataire(**kwargs))
        if liste_ajouts:
            # Enregistre les destinataires
            Destinataire.objects.bulk_create(liste_ajouts)
            # Associe les destinataires au mail
            destinataires = Destinataire.objects.filter(pk__gt=idmax)
            ThroughModel = Mail.destinataires.through
            ThroughModel.objects.bulk_create([ThroughModel(mail_id=mail.pk, destinataire_id=destinataire.pk) for destinataire in destinataires])

        # Suppression des destinataires
        for id in liste_id:
            if id not in liste_selections:
                kwargs = {"{0}_id".format(self.categorie): id, "mail": mail}
                destinataire = Destinataire.objects.get(**kwargs)
                destinataire.delete()

        return HttpResponseRedirect(reverse_lazy("editeur_emails", kwargs={'pk': mail.pk}))
