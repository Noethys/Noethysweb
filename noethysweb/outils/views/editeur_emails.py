# -*- coding: utf-8 -*-
# Copyright (c) 2019-2021 Ivan LUCAS.
# Noethysweb, application de gestion multi-activités.
# Distribué sous licence GNU GPL.

import json, os, uuid
from collections import defaultdict

from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Count
from django.contrib import messages
from django.conf import settings

from core.views import crud
from core.models import ModeleEmail, Mail, PieceJointe, Destinataire, Famille, Individu, Activite, Inscription, Collaborateur, Contact, SignatureEmail, PortailParametre
from core.utils import utils_texte
from outils.forms.editeur_emails import Formulaire
from outils.utils import utils_email

def RemoveDuplicates(mail):
    """
    Supprime en base les doublons d'adresse pour un même Mail,
    en ne gardant que la première occurrence pour chaque adresse.
    """
    groups = defaultdict(list)
    for d in mail.destinataires.all():
        addr_norm = (d.adresse or "").strip().lower()
        groups[addr_norm].append(d)

    for addr_norm, items in groups.items():
        if len(items) > 1:
            to_keep = items[0]  # On garde le premier
            for d in items[1:]:
                d.delete()


def Get_modele_email(request):
    """Renvoie le contenu HTML d'un modèle d'emails"""
    idmodele = int(request.POST.get("idmodele"))
    modele = ModeleEmail.objects.filter(pk=idmodele).first()
    return JsonResponse({"objet": modele.objet, "html": modele.html})


def Get_signature_email(request):
    """Renvoie le contenu HTML d'une signature d'emails"""
    idsignature = int(request.POST.get("idsignature"))
    signature = SignatureEmail.objects.filter(pk=idsignature).first()
    return JsonResponse({"html": signature.html})


def Exporter_excel(request):
    """Exporte la liste des destinataires ou des envois vers un fichier Excel"""
    idmail = int(request.POST.get("idmail") or 0)
    mode = request.POST.get("mode")

    # --- Fetch the Mail ---
    try:
        mail = Mail.objects.get(pk=idmail)
    except Mail.DoesNotExist:
        return JsonResponse({"erreur": "Mail inexistant."}, status=401)

    destinataires = (
        mail.destinataires
        .select_related("famille", "individu", "activites", "inscription", "contact", "collaborateur")
        .order_by("adresse")
    )

    if not destinataires.exists():
        return JsonResponse({"erreur": "Aucun destinataire n'a été sélectionné"}, status=401)

    # Création du répertoire et du nom du fichier
    rep_temp = os.path.join("temp", str(uuid.uuid4()))
    rep_destination = os.path.join(settings.MEDIA_ROOT, rep_temp)
    if not os.path.isdir(rep_destination):
        os.makedirs(rep_destination)
    nom_fichier = f"export_{mode}.xlsx"

    # Création du classeur Excel (xlsxwriter)
    import xlsxwriter
    classeur = xlsxwriter.Workbook(os.path.join(rep_destination, nom_fichier))
    feuille = classeur.add_worksheet(mode)

    # Colonnes si on exporte les "envois"
    if mode == "envois":
        colonnes = (
            "Famille", "Individu", "Activité", "Inscription",
            "Collaborateur", "Contact", "Email", "Résultat de l'envoi"
        )
        for num_colonne, label_colonne in enumerate(colonnes):
            feuille.set_column(num_colonne, num_colonne, 35)
            feuille.write(0, num_colonne, label_colonne)

    # Remplir le classeur
    for num_ligne, destinataire in enumerate(destinataires):
        if mode == "destinataires":
            # Juste la colonne avec l'adresse
            feuille.write(num_ligne, 0, destinataire.adresse)
        if mode == "envois":
            # Remplir chaque colonne
            feuille.write(num_ligne+1, 0, destinataire.famille.nom if destinataire.famille else "")
            feuille.write(num_ligne+1, 1, destinataire.individu.Get_nom() if destinataire.individu else "")
            feuille.write(num_ligne+1, 2, destinataire.activites.nom if destinataire.activites else "")
            feuille.write(num_ligne+1, 3, destinataire.inscription.Get_nom() if destinataire.inscription else "")
            feuille.write(num_ligne+1, 4, destinataire.collaborateur.Get_nom() if destinataire.collaborateur else "")
            feuille.write(num_ligne+1, 5, destinataire.contact.Get_nom() if destinataire.contact else "")
            feuille.write(num_ligne+1, 6, destinataire.adresse)
            feuille.write(num_ligne+1, 7, destinataire.resultat_envoi)

    classeur.close()
    return JsonResponse({"nom_fichier": os.path.join(rep_temp, nom_fichier)})


class Page(crud.Page):
    """Page principale de l'éditeur d'emails"""
    model = Mail
    menu_code = "editeur_emails"
    template_name = "outils/editeur_emails.html"

    def Get_idmail(self):
        return self.kwargs.get('pk', None)

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = "Envoi d'emails par lot"

        mail = None
        if self.Get_idmail():
            mail = Mail.objects.get(pk=self.Get_idmail())
        context['mail'] = mail

        # --- Supprimer les doublons si mail existe ---
        if mail:
            RemoveDuplicates(mail)

        # Charger la catégorie, les signatures, etc.
        categorie = mail.categorie if mail else "saisie_libre"
        context['modeles'] = ModeleEmail.objects.filter(categorie=categorie)
        context['signatures'] = SignatureEmail.objects.filter(
            Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True)
        )

        # Stats par catégorie
        context['categories'] = {}
        if mail:
            categories_data = (
                Destinataire.objects
                .values('categorie')
                .filter(mail=mail)
                .annotate(nbre=Count('pk', distinct=True))
            )
            for item in categories_data:
                cat = item["categorie"]
                if cat == "famille":
                    count_value = Destinataire.objects.filter(mail=mail, categorie=cat).values('famille').distinct().count()
                elif cat == "activites":
                    count_value = Destinataire.objects.filter(mail=mail, categorie=cat).values('activite').distinct().count()
                elif cat == "individu":
                    count_value = Destinataire.objects.filter(mail=mail, categorie=cat).values('individu').distinct().count()
                else:
                    count_value = item["nbre"]
                context['categories'][cat] = count_value

        # Récupérer tous les destinataires (il n'y a plus de doublons, thanks to RemoveDuplicates)
        destinataires = []
        nbre_envois_attente = 0
        nbre_envois_reussis = 0
        nbre_envois_echec = 0

        if mail:
            for d in (
                mail.destinataires
                .select_related("famille", "individu", "activites", "inscription", "contact", "collaborateur")
                .prefetch_related("documents")
                .order_by("adresse")
            ):
                destinataires.append(d)
                if not d.resultat_envoi:
                    nbre_envois_attente += 1
                elif d.resultat_envoi == "ok":
                    nbre_envois_reussis += 1
                else:
                    nbre_envois_echec += 1

        context['destinataires'] = destinataires
        context['nbre_envois_attente'] = nbre_envois_attente
        context['nbre_envois_reussis'] = nbre_envois_reussis
        context['nbre_envois_echec'] = nbre_envois_echec

        # Intro envois
        intro_envois = []
        if not destinataires:
            intro_envois.append("Aucun envoi")
        if nbre_envois_reussis == 1:
            intro_envois.append("1 envoi réussi")
        elif nbre_envois_reussis > 1:
            intro_envois.append(f"{nbre_envois_reussis} envois réussis")

        if nbre_envois_attente == 1:
            intro_envois.append("1 envoi en attente")
        elif nbre_envois_attente > 1:
            intro_envois.append(f"{nbre_envois_attente} envois en attente")

        if nbre_envois_echec == 1:
            intro_envois.append("1 envoi en échec")
        elif nbre_envois_echec > 1:
            intro_envois.append(f"{nbre_envois_echec} envois en échec")

        context['intro_envoi'] = utils_texte.Convert_liste_to_texte_virgules(intro_envois)

        # Parametres
        parametres_db = PortailParametre.objects.filter(
            code__in=[
                "emails_individus_afficher_page",
                "emails_familles_afficher_page",
                "emails_activites_afficher_page",
                "emails_inscriptions_afficher_page",
                "emails_collaborateurs_afficher_page",
                "emails_liste_diffusion_afficher_page",
            ]
        )
        parametres = {}
        for p in parametres_db:
            if isinstance(p.valeur, str):
                parametres[p.code] = p.valeur.strip().lower() in ["true", "1"]

        context["parametres"] = parametres
        return context

    def get_form_kwargs(self, **kwargs):
        """Envoie l'idmail au formulaire"""
        form_kwargs = super().get_form_kwargs(**kwargs)
        form_kwargs["idmail"] = self.Get_idmail()
        return form_kwargs

    def post(self, request, *args, **kwargs):
        """Gère la sauvegarde du Mail ou la redirection vers la sélection de destinataires."""
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        idmail = self.Get_idmail()
        if idmail:
            mail = Mail.objects.get(pk=idmail)
            mail.objet = form.cleaned_data["objet"]
            mail.html = form.cleaned_data["html"]
            mail.adresse_exp = form.cleaned_data["adresse_exp"]
            mail.selection = form.cleaned_data["selection"]
            mail.save()
        else:
            mail = Mail.objects.create(
                categorie="saisie_libre",
                objet=form.cleaned_data["objet"],
                html=form.cleaned_data["html"],
                adresse_exp=form.cleaned_data["adresse_exp"],
                selection=form.cleaned_data["selection"],
                utilisateur=request.user,
            )
            messages.info(request, "Un brouillon du mail a été enregistré")

        # Gérer les pièces jointes
        piece = request.FILES.get('pieces_jointes')
        if piece:
            piece_jointe = PieceJointe.objects.create(nom=piece._name, fichier=piece)
            mail.pieces_jointes.add(piece_jointe)

        suppr_piece_jointe = request.POST.get("suppr_piece_jointe")
        if suppr_piece_jointe:
            PieceJointe.objects.filter(pk=suppr_piece_jointe).delete()

        # Gérer la redirection pour ajouter des destinataires
        action = request.POST.get("action")
        if action == "ajouter_familles":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_familles", kwargs={"idmail": mail.pk}))
        if action == "ajouter_individus":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_individus", kwargs={"idmail": mail.pk}))
        if action == "ajouter_activites":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_activites"))
        if action == "ajouter_inscription":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_inscriptions"))
        if action == "ajouter_collaborateurs":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_collaborateurs", kwargs={"idmail": mail.pk}))
        if action == "ajouter_contacts":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_contacts", kwargs={"idmail": mail.pk}))
        if action == "ajouter_diffusion":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_listes_diffusion", kwargs={"idmail": mail.pk}))
        if action == "ajouter_saisie_libre":
            return HttpResponseRedirect(reverse_lazy("editeur_emails_saisie_libre", kwargs={"idmail": mail.pk}))

        # Gérer l'envoi
        if action == "envoyer":
            # Vérifier la validité minimale
            if mail.destinataires.count() == 0:
                messages.error(request, "Vous devez sélectionner au moins un destinataire")
            elif not form.cleaned_data["adresse_exp"]:
                messages.error(request, "Vous devez sélectionner une adresse d'expédition dans la liste")
            elif not form.cleaned_data["objet"]:
                messages.error(request, "Vous devez saisir un objet")
            elif not form.cleaned_data["html"]:
                messages.error(request, "Vous devez saisir un texte")
            else:
                # Définir la variable expediteur_email
                expediteur_email = mail.adresse_exp
                # Récupérer tous les destinataires existants de type "expediteur"
                destinataires_expediteurs = list(mail.destinataires.filter(categorie="expediteur"))
                # Comparaison en mémoire pour éviter l'erreur sur EncryptedEmailField
                already_there = any(str(dest.adresse) == str(expediteur_email) for dest in destinataires_expediteurs)

                # Ajouter l'expéditeur seulement s'il n'existe pas déjà
                if not already_there:
                    destinataire_expediteur = Destinataire.objects.create(
                        categorie="expediteur",
                        adresse=expediteur_email
                    )
                    mail.destinataires.add(destinataire_expediteur)  # Ajout au ManyToMany
                utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)

        return HttpResponseRedirect(reverse_lazy("editeur_emails", kwargs={'pk': mail.pk}))


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire


class Modifier(Page, crud.Modifier):
    form_class = Formulaire


# --------------------------------------------------------------------------
# Pages d'ajout de destinataires (familles, individus, etc.)
# --------------------------------------------------------------------------

class Page_destinataires(crud.Page):
    menu_code = "editeur_emails"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_titre'] = "Editeur d'emails"
        context['idmail'] = self.kwargs.get("idmail")
        context['categorie'] = self.categorie
        return context

    def post(self, request, **kwargs):
        liste_selections = json.loads(request.POST.get("selections") or "[]")
        mail = Mail.objects.get(pk=self.kwargs.get("idmail"))

        dict_adresses = {}
        if self.categorie == "famille":
            dict_adresses = {
                f.pk: f.mail
                for f in Famille.objects.filter(email_blocage=False)
            }
        elif self.categorie == "individu":
            dict_adresses = {
                i.pk: i.mail
                for i in Individu.objects.all()
            }
        elif self.categorie == "activites":
            inscriptions = (
                Inscription.objects
                .filter(activite_id__in=liste_selections, famille__isnull=False)
                .select_related("famille")
            )
            for ins in inscriptions:
                if ins.famille and ins.famille.mail:
                    dict_adresses[ins.famille.pk] = ins.famille.mail
        elif self.categorie == "collaborateur":
            dict_adresses = {
                c.pk: c.mail
                for c in Collaborateur.objects.all()
            }
        elif self.categorie == "contact":
            dict_adresses = {
                c.pk: c.mail
                for c in Contact.objects.all()
            }

        # Destinataires déjà existants pour cette catégorie
        destinataires_existants = mail.destinataires.filter(categorie=self.categorie)
        liste_id_existants = [
            getattr(dest, f"{self.categorie}_id") for dest in destinataires_existants
        ]

        # ### AJOUT : On construit un set des adresses déjà présentes (pour ce mail),
        #             afin d'éviter les doublons en base
        existing_addresses = set(
            str(d.adresse).strip().lower()
            for d in mail.destinataires.all()
            if d.adresse
        )

        # On repère la fin de la table pour faire le bulk_create
        dernier = Destinataire.objects.last()
        idmax = dernier.pk if dernier else 0

        liste_ajouts = []
        for ident in dict_adresses:
            # Ne pas ajouter deux fois la même "famille_id"/"individu_id", etc.
            if ident not in liste_id_existants:
                adresse = dict_adresses[ident]
                if adresse:
                    addr_norm = adresse.strip().lower()
                    # Vérifier si cette adresse est déjà utilisée
                    if addr_norm not in existing_addresses:
                        existing_addresses.add(addr_norm)  # Évite de l'ajouter encore
                        if self.categorie == "activites":
                            liste_ajouts.append(Destinataire(
                                categorie="activites",
                                famille_id=ident,
                                adresse=adresse
                            ))
                        else:
                            kwargs2 = {
                                f"{self.categorie}_id": ident,
                                "categorie": self.categorie,
                                "adresse": adresse,
                            }
                            liste_ajouts.append(Destinataire(**kwargs2))

        if liste_ajouts:
            Destinataire.objects.bulk_create(liste_ajouts)
            nouveaux = Destinataire.objects.filter(pk__gt=idmax)
            mail.destinataires.add(*nouveaux)

        # Suppression si décoché
        for ident in liste_id_existants:
            if ident not in dict_adresses:
                qs_suppr = destinataires_existants.filter(**{f"{self.categorie}_id": ident})
                qs_suppr.delete()

        return HttpResponseRedirect(reverse_lazy("editeur_emails", kwargs={'pk': mail.pk}))
