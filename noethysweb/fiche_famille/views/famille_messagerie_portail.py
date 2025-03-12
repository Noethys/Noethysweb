# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views import crud
from fiche_famille.views.famille import Onglet
from core.models import PortailMessage, Structure
from outils.forms.messagerie_portail import Formulaire, Envoi_notification_message
from django.db.models import Q, Count
from core.models import Individu
from core.models import Rattachement
from core.models import Famille
import logging, datetime, json

class Page(Onglet):
    model = PortailMessage

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = "messagerie"

        idfamille = self.kwargs.get('idfamille', None)
        idstructure = self.kwargs.get('idstructure', None)
        idindividu = self.kwargs.get('idindividu', None)

        print(f"ID Famille: {idfamille}, ID Structure: {idstructure}, ID Individu: {idindividu}")

        # ---- 1) Préparer liste des structures auxquelles au moins un individu de la famille est inscrit via une activité ----
        context['liste_structures'] = (
            Structure.objects
            # 1) Filtrer sur l'accès utilisateur (si nécessaire)
            .filter(pk__in=self.request.user.structures.all())
            # 2) Filtrer sur "structures liées à la famille via inscriptions"
            .filter(activite__inscription__famille_id=self.Get_idfamille())
            .order_by("nom")
            .distinct()
        )

        # ---- 2) Préparer la liste des individus (représentants) si la famille existe ----
        if self.Get_idfamille():
            context['liste_representants'] = (
                Individu.objects
                .filter(rattachement__famille_id=self.Get_idfamille(),
                        rattachement__titulaire=True)
            )

        # ---- 3) Récupérer l'individu sélectionné (si idindividu est passé dans l'URL) ----
        if idindividu:
            try:
                context['individu_selectionne'] = Individu.objects.get(idindividu=idindividu)
            except Individu.DoesNotExist:
                context['individu_selectionne'] = None
        else:
            context['individu_selectionne'] = None

        # ---- 4) Récupérer la famille sélectionnée ----
        if self.Get_idfamille():
            context["famille"] = Famille.objects.get(pk=self.Get_idfamille())

        # ---- 5) Récupérer la structure sélectionnée ----
        if self.get_idstructure():
            context["structure"] = Structure.objects.get(pk=self.get_idstructure())

        # -------------------------------------------------------------------
        #              COMPTAGE DU NOMBRE DE MESSAGES
        # -------------------------------------------------------------------
        #
        # a) Comptage des messages "famille" (individu_id IS NULL)
        qs_famille = (
            PortailMessage.objects
            .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                  "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
            .values("famille", "structure")
            .filter(individu__isnull=True)    # => messages pour la famille
            .annotate(nbre=Count("pk"))
        )
        # On construit un dict : clé = (famille_id, structure_id), valeur = nbre de messages
        dict_messages_par_famille = {}
        for val in qs_famille:
            dict_messages_par_famille[
                (val["famille"], val["structure"])
            ] = val["nbre"]

        # b) Comptage des messages "individu" (individu_id non nul)
        qs_individu = (
            PortailMessage.objects
            .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                  "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
            .values("famille", "structure", "individu")
            .filter(individu__isnull=False)  # => messages privés à un individu
            .annotate(nbre=Count("pk"))
        )
        # On construit un dict : clé = (famille_id, structure_id, individu_id), valeur = nbre
        dict_messages_par_individu = {}
        for val in qs_individu:
            dict_messages_par_individu[
                (val["famille"], val["structure"], val["individu"])
            ] = val["nbre"]
        # c) Comptage global : tous messages confondus
        qs_total = (
            PortailMessage.objects
            .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                  "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
            .values("famille", "structure")
            .annotate(nbre=Count("pk"))  # pas de .filter(individu__isnull=...)
        )

        dict_messages_par_structure = {}
        for val in qs_total:
            dict_messages_par_structure[
                (val["famille"], val["structure"])
            ] = val["nbre"]

        # On stocke ces trois dictionnaires dans le contexte
        context["dict_messages_par_famille"] = dict_messages_par_famille
        context["dict_messages_par_individu"] = dict_messages_par_individu
        context["dict_messages_par_structure"] = dict_messages_par_structure

        # -------------------------------------------------------------------
        #              COMPTAGE DU NOMBRE DE MESSAGES NON LUS
        # -------------------------------------------------------------------
        #
        # a) Calcul des messages non lus par structure
        qs_non_lus = (
            PortailMessage.objects
            .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                  "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
            .values("structure")
            .filter(
                famille_id=self.Get_idfamille(),
                utilisateur__isnull=False,
                date_lecture__isnull=True,
            )
            .exclude(utilisateur=self.request.user)
            .annotate(nbre=Count('pk'))
        )
        # Création d'un dictionnaire {structure_id: nombre_de_messages_non_lus}
        dict_messages_non_lus_structure = {}
        for val in qs_non_lus:
            dict_messages_non_lus_structure[val["structure"]] = val["nbre"]


        # b) Calcul des messages non lus par famille
        qs_non_lus_family = (
            PortailMessage.objects
            .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                  "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
            .values("famille")
            .filter(
                famille_id=self.Get_idfamille(),
                utilisateur__isnull=False,
                individu__isnull=True,
                date_lecture__isnull=True,
            )
            .exclude(utilisateur=self.request.user)
            .annotate(nbre=Count('pk'))
        )
        # Création d'un dictionnaire {famille_id: nombre_de_messages_non_lus}
        dict_messages_non_lus_family= {}
        for val in qs_non_lus_family:
            dict_messages_non_lus_family[val["famille"]] = val["nbre"]


        # c) Calcul des messages non lus par individu
        qs_non_lus_individu = (
            PortailMessage.objects
            .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
            .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                  "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
            .values("individu")
            .filter(
                famille_id=self.Get_idfamille(),
                utilisateur__isnull=False,
                individu__isnull=False,
                date_lecture__isnull=True,
            )
            .exclude(utilisateur=self.request.user)
            .annotate(nbre=Count('pk'))
        )

        # Création d'un dictionnaire {individu_id: nombre_de_messages_non_lus}
        dict_messages_non_lus_individu= {}
        for val in qs_non_lus_individu:
            dict_messages_non_lus_individu[val["individu"]] = val["nbre"]

        # Ajout au contexte
        context['dict_messages_non_lus_structure'] = dict_messages_non_lus_structure
        context['dict_messages_non_lus_family'] = dict_messages_non_lus_family
        context['dict_messages_non_lus_individu'] = dict_messages_non_lus_individu

        # -------------------------------------------------------------------
        #              AFFICHAGE DE LA DISCUSSION
        # -------------------------------------------------------------------
        #
        # Si idindividu est renseigné => discussion individuelle
        # Sinon => discussion familiale
        if idindividu:
            # Discussion avec un individu particulier
            liste_messages_discussion = (
                PortailMessage.objects
                .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
                .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                      "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
                .select_related("structure", "utilisateur")
                .filter(
                    structure_id=self.get_idstructure(),
                    famille_id=self.Get_idfamille(),
                    individu_id=idindividu
                )
                .order_by("date_creation")
            )

        else:
            # Discussion générale avec la famille (individu_id=NULL)
            liste_messages_discussion = (
                PortailMessage.objects
                .select_related("famille", "structure", "individu", "utilisateur")  # Charge en une seule requête
                .only("idmessage", "famille_id", "structure_id", "individu_id", "utilisateur_id", "texte",
                      "date_creation", "date_lecture")  # Charge seulement les colonnes nécessaires
                .select_related("structure", "utilisateur")
                .filter(
                    famille_id=self.Get_idfamille(),
                    structure_id=self.get_idstructure(),
                    individu__isnull=True
                )
                .order_by("date_creation")
            )

        # Ajouter les messages non lus au contexte
        liste_messages_non_lus = liste_messages_discussion.filter(
           date_lecture__isnull=True
        ).exclude(utilisateur=self.request.user)
        context['liste_messages_non_lus'] = list(liste_messages_non_lus)

        # Marquer les messages non lus comme lus
        liste_messages_non_lus.update(date_lecture=datetime.datetime.now())
        context['liste_messages_discussion'] = liste_messages_discussion
        # liste_messages_discussion.update(date_lecture=datetime.datetime.now())

        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idstructure"] = self.get_idstructure()
        form_kwargs["idfamille"] = self.Get_idfamille()
        idindividu = self.kwargs.get('idindividu', None)
        return form_kwargs

    def get_idstructure(self):
        return self.kwargs.get("idstructure", 0)

    def Get_idfamille(self):
        return self.kwargs.get("idfamille", 0)

    def get_success_url(self):
        """ Rediriger vers la discussion appropriée après l’envoi du message. """
        idindividu = self.kwargs.get('idindividu', None)

        if idindividu:
            # Discussion individuelle
            return reverse_lazy("famille_messagerie_portail", kwargs={
                'idstructure': self.get_idstructure(),
                'idfamille': self.Get_idfamille(),
                'idindividu': idindividu
            })
        else:
            # Discussion familiale
            return reverse_lazy("famille_messagerie_portail", kwargs={
                'idstructure': self.get_idstructure(),
                'idfamille': self.Get_idfamille()
            })


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_messagerie_portail.html"
    texte_confirmation = "Le message a bien été envoyé"

    def form_valid(self, form):
        """ Envoie une notification de nouveau message à la famille ou au représentant par email """
        idfamille = self.kwargs.get('idfamille', None)
        idindividu = self.kwargs.get('idindividu', None)
        structure = self.kwargs.get('idstructure', None)
        # 2) On fait un commit=False pour pouvoir modifier l’objet avant l’enregistrement
        message = form.save(commit=False)

        # 3) On renseigne individuellement les champs voulus
        message.famille_id = self.Get_idfamille()  # la famille
        message.structure_id = self.get_idstructure()  # la structure
        message.utilisateur_id = self.request.user.pk  # utilisateur qui envoie (admin ?)

        if idindividu:
            message.individu_id = idindividu  # discussion privée
        else:
            message.individu_id = None  # discussion famille

        # On sauvegarde en base
        message.save()

        # 4) Envoyer la notification si besoin
        if idfamille:
            Envoi_notification_message(
                request=self.request,
                famille=idfamille,
                structure=structure
            )
        elif idindividu:
            Envoi_notification_message(
                request=self.request,
                individu=idindividu,
                structure=structure
            )

        return super(Ajouter, self).form_valid(form)
