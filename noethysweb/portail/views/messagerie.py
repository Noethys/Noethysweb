# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json
from core.models import Famille
from core.models import Rattachement
from core.models import Individu
from django.db.models import Count, QuerySet
from core.models import AdresseMail
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.template.defaultfilters import truncatechars, striptags
from django.utils.translation import gettext as _
from core.views import crud
from core.models import PortailMessage, Structure, Mail, Destinataire
from core.utils import utils_portail
from outils.utils import utils_email
from portail.forms.messagerie import Formulaire
from portail.views.base import CustomView
from django.db.models import Q

class Page(CustomView):
    model = PortailMessage
    menu_code = "portail_contact"

    def get_famille_object(self):
        idstructure = self.kwargs.get("idstructure", None)
        if not idstructure:
            return None

        # Vérifier que la structure existe
        try:
            structure = Structure.objects.get(pk=idstructure)
        except Structure.DoesNotExist:
            return None

        # Récupérer les familles associées à l'utilisateur
        if hasattr(self.request.user, 'famille'):
            familles = [self.request.user.famille]
        elif hasattr(self.request.user, 'individu'):
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            familles = [
                rattachement.famille for rattachement in rattachements
                if rattachement.famille and rattachement.titulaire == 1
            ]
        else:
            familles = []

        # Retourner toutes les familles associées à l'utilisateur
        return Famille.objects.filter(pk__in=[fam.pk for fam in familles])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        idstructure = self.kwargs.get("idstructure")
        idfamille = self.kwargs.get("idfamille")
        idindividu = self.kwargs.get("idindividu")

        # Récupérer la structure
        structure = Structure.objects.get(pk=idstructure)
        context["structure"] = structure

        # Récupérer les familles liées à l'utilisateur
        familles = self.get_famille_object()
        context["familles"] = familles
        context["familles_count"] = familles.count()

        # Récupérer l'individu connecté
        individu_connecte = getattr(self.request.user, 'individu', None)
        context["individu_connecte"] = individu_connecte

        # Gérer le cas d'une seule famille
        if familles.count() == 1:
            single_family = familles.first()
            context["discussion_famille"] = single_family
            context["discussion_type"] = "famille"

        # Construction du filtre conditionnel selon la catégorie de l'utilisateur
        if self.request.user.categorie == "individu" and hasattr(self.request.user, "individu"):
            extra_filter = Q(individu=self.request.user.individu) | Q(individu__isnull=True)
        elif self.request.user.categorie == "famille" and hasattr(self.request.user, "famille"):
            extra_filter = Q(famille=self.request.user.famille) | Q(famille__isnull=True)
        else:
            extra_filter = Q()  # Ou lever une exception selon votre logique métier
        # Calculer les messages non lus pour chaque famille
        unread_messages_by_family = (
            PortailMessage.objects
            .select_related("famille", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "individu_id", "utilisateur_id", "texte", "date_creation",
                  "date_lecture")  # Charge seulement les colonnes nécessaires
            .filter(
                Q(famille__in=familles),
                Q(utilisateur__isnull=False),
                Q(date_lecture__isnull=True),
                extra_filter  # Filtre conditionnel selon la catégorie
            )
            .exclude(utilisateur=self.request.user)  # Exclure les messages envoyés par l'utilisateur connecté
            .values("famille")
            .annotate(unread_count=Count("famille"))
        )
        context["unread_messages_by_family"] = {
            item["famille"]: item["unread_count"] for item in unread_messages_by_family
        }

        # Calculer les messages non lus en famille (individu NULL)
        unread_messages_family = (
            PortailMessage.objects
            .select_related("famille", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "individu_id", "utilisateur_id", "texte", "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
            .filter(
                Q(famille__in=familles),
                Q(utilisateur__isnull=False),
                Q(date_lecture__isnull=True),
                Q(individu__isnull=True)
            )
            .exclude(utilisateur=self.request.user)
            .values("famille")
            .annotate(unread_count=Count("famille"))
        )
        context["unread_messages_family"] = {
            item["famille"]: item["unread_count"] for item in unread_messages_family
        }

        # Calculer les messages non lus pour l'individu connecté
        unread_messages_private = {}
        if individu_connecte:
            unread_messages_private = (
                PortailMessage.objects
                .select_related("famille", "individu", "utilisateur")  # Charge en une seule requête
                .only("idmessage", "famille_id", "individu_id", "utilisateur_id", "texte",
                      "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
                .filter(
                    Q(famille__in=familles),
                    Q(utilisateur__isnull=False),
                    Q(date_lecture__isnull=True),
                    Q(individu=individu_connecte)
                )
                .exclude(utilisateur=self.request.user)
                .values("famille")
                .annotate(unread_count=Count("famille"))
            )
            context["unread_messages_private"] = {
                item["famille"]: item["unread_count"] for item in unread_messages_private
            }
        else:
            context["unread_messages_private"] = {}

        # Gestion des discussions
        if idindividu:
            # Discussion individuelle
            individu = Individu.objects.get(pk=idindividu)
            famille = Famille.objects.get(pk=idfamille)

            context["discussion_type"] = "individu"
            context["discussion_individu"] = individu
            context["discussion_famille"] = famille

            # Messages de la discussion individuelle
            liste_messages = (
                PortailMessage.objects
                .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
                .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                      "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
                .filter(
                structure=structure,
                famille=famille,
                individu=individu
            ).order_by("date_creation"))
            context["liste_messages"] = liste_messages

        elif idfamille:
            # Discussion familiale
            famille = Famille.objects.get(pk=idfamille)
            context["discussion_type"] = "famille"
            context["discussion_famille"] = famille

            # Messages de la discussion familiale
            liste_messages = (
                PortailMessage.objects
                .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
                .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                      "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
                .filter(
                structure=structure,
                famille=famille,
                individu__isnull=True
            ).order_by("date_creation"))
            context["liste_messages"] = liste_messages

            # Ajouter les messages spécifiques à cette famille
            context["unread_count_famille"] = context["unread_messages_by_family"].get(idfamille, 0)

        else:
            # Aucune discussion sélectionnée
            context["discussion_type"] = None
            context["liste_messages"] = PortailMessage.objects.none()
        # Calcul des messages non lus dans la discussion actuelle
        liste_messages_non_lus = context["liste_messages"].filter(date_lecture__isnull=True).exclude(
            utilisateur=self.request.user)
        context["liste_messages_non_lus"] = list(liste_messages_non_lus)

        # Marquer comme lus les messages affichés
        liste_messages_non_lus.update(date_lecture=datetime.datetime.now())

        logger.info(f"idstructure: {idstructure}, idfamille: {idfamille}, idindividu: {idindividu}")
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idstructure"] = self.get_idstructure()
        return form_kwargs

    def get_idstructure(self):
        return self.kwargs.get("idstructure", 0)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/messagerie.html"
    texte_confirmation = _("Le message a bien été envoyé")
    titre_historique = "Ajouter un message"


    def form_valid(self, form):
        message = form.save(commit=False)

        idstructure = self.kwargs["idstructure"]
        idfamille = self.kwargs.get("idfamille", None)
        idindividu = self.kwargs.get("idindividu", None)

        message.structure_id = idstructure
        message.utilisateur_id = self.request.user.pk
        message.date_creation = datetime.datetime.now()

        if idindividu:
            # discussion privée
            message.individu_id = idindividu
            message.famille_id = idfamille
        elif idfamille:
            # discussion familiale
            message.famille_id = idfamille
            message.individu_id = None
        else:
            # Enregistrer l'individu connecté si l'utilisateur est un individu
            if hasattr(self.request.user, 'individu'):
                message.individu_id = self.request.user.individu.pk
        message.save()

        return super().form_valid(form)

    def get_success_url(self):
        idstructure = self.kwargs["idstructure"]
        idfamille = self.kwargs.get("idfamille", None)
        idindividu = self.kwargs.get("idindividu", None)

        if idindividu:
            return reverse_lazy("portail_messagerie_individu", kwargs={
                "idstructure": idstructure,
                "idfamille": idfamille,
                "idindividu": idindividu
            })
        elif idfamille:
            return reverse_lazy("portail_messagerie_famille", kwargs={
                "idstructure": idstructure,
                "idfamille": idfamille
            })
        return reverse_lazy("portail_contact")

    def Get_detail_historique(self, instance):
        return "Destinataire=%s Texte=%s" % (instance.structure, truncatechars(striptags(instance.texte), 40))

    def Apres_form_valid(self, form=None, instance=None):
        """Envoie une notification de nouveau message à l'administrateur par email"""
        try:
            # Éviter les doublons
            self._already_executed = getattr(self, "_already_executed", False)
            if self._already_executed:
                logger.warning("Apres_form_valid a déjà été exécuté. Ignoré.")
                return
            self._already_executed = True

            # Vérifiez si l'envoi de notification est activé
            parametres_portail = utils_portail.Get_dict_parametres()
            if not parametres_portail.get("messagerie_envoyer_notification_admin", False):
                logger.info("Notification admin désactivée dans les paramètres.")
                return

            # Récupérer la structure concernée
            structure = Structure.objects.get(pk=self.get_idstructure())
            if not structure.adresse_exp:
                logger.error("Erreur : Adresse email d'expédition (adresse_exp) manquante pour la structure.")
                return

            # Récupérer l'individu connecté
            individu_connecte = getattr(self.request.user, 'individu', None)
            if not individu_connecte:
                logger.error("Erreur : Aucun individu connecté trouvé.")
                return

            # Vérifier si l'individu connecté a une adresse email
            email_individu = getattr(individu_connecte, 'mail', None)
            if not email_individu:
                logger.error("Erreur : Aucun email trouvé pour l'individu connecté.")
                return

            # Convertir ou associer l'email de l'individu à une instance d'AdresseMail
            adresse_exp = AdresseMail.objects.filter(adresse=email_individu).first()
            if not adresse_exp:
                adresse_exp = AdresseMail.objects.create(adresse=email_individu)
                logger.info(f"Nouvelle adresse email créée : {adresse_exp.adresse}")

            # Récupérer un individu si concerné
            idindividu = self.kwargs.get("idindividu", None)
            individu = Individu.objects.get(pk=idindividu) if idindividu else None
            famille = self.get_famille_object()
            # Par défaut, on considère une discussion liée à la famille
            if isinstance(famille, QuerySet):
                famille = famille.first()
            if not famille:
                logger.error("Erreur : Famille non trouvée pour l'utilisateur.")
                return

            # Créer l'URL du message
            if individu:
                url_message = self.request.build_absolute_uri(
                    reverse_lazy("portail_messagerie_individu", kwargs={
                        "idstructure": structure.pk,
                        "idfamille": famille.pk,
                        "idindividu": individu.pk
                    })
                )
            else:

                url_message = self.request.build_absolute_uri(
                    reverse_lazy("portail_messagerie_famille", kwargs={
                        "idstructure": structure.pk,
                        "idfamille": famille.pk
                    })
                )

            # Préparer le contenu de l'email
            contenu_message = f"""
            <p>Bonjour,</p>
            <p>Vous avez reçu un nouveau message de <b>{individu_connecte.Get_nom()}</b> qui appartient à la famille <b>{famille}</b> sur le portail.</p>
            <p>Vous pouvez le consulter et y répondre en cliquant sur le lien suivant : <a href="{url_message}" target="_blank">Accéder au message</a>.</p>
            <p>L'administrateur du portail</p>
            """

            # Créer un objet Mail
            mail = Mail.objects.create(
                categorie="saisie_libre",
                objet="Nouveau message sur le portail",
                html=contenu_message,
                adresse_exp=adresse_exp,  # Utilisation de l'instance AdresseMail
                utilisateur=self.request.user if self.request else None,
            )
            logger.debug(f"Mail créé : {mail}")
            # logger.debug(f"Mail créé : {mail}, Type : {type(mail)}")


            # Ajouter un destinataire au mail
            destinataire = Destinataire.objects.create(
                categorie="saisie_libre",
                adresse=structure.adresse_exp.adresse,  # L'email de l'administrateur
            )
            mail.destinataires.add(destinataire)
            # Envoyer l'email
            utils_email.Envoyer_model_mail(idmail=mail.pk, request=self.request)
            logger.info(f"Notification email envoyée avec succès de {adresse_exp.adresse} à {structure.adresse_exp.adresse}.")

        except Structure.DoesNotExist:
            logger.error("Erreur : La structure spécifiée n'existe pas.")
        except Individu.DoesNotExist:
            logger.error("Erreur : L'individu spécifié n'existe pas.")
        except Exception as err:
            logger.error(f"Erreur dans l'envoi de la notification de message par email à l'administrateur : {err}")
