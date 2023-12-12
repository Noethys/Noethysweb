# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, datetime, json
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


class Page(CustomView):
    model = PortailMessage
    menu_code = "portail_contact"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = _("Messagerie")
        context['structure'] = Structure.objects.get(pk=self.get_idstructure())
        context['liste_messages'] = PortailMessage.objects.select_related("famille", "utilisateur").filter(famille=self.request.user.famille, structure_id=self.get_idstructure()).order_by("date_creation")

        # Importation des messages non lus
        liste_messages_non_lus = PortailMessage.objects.select_related("famille").filter(famille=self.request.user.famille, structure_id=self.get_idstructure(), utilisateur__isnull=False, date_lecture__isnull=True)
        context['liste_messages_non_lus'] = list(liste_messages_non_lus)

        # Enregistre la date de lecture pour les messages non lus
        liste_messages_non_lus.update(date_lecture=datetime.datetime.now())
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idstructure"] = self.get_idstructure()
        return form_kwargs

    def get_idstructure(self):
        return self.kwargs.get("idstructure", 0)

    def get_success_url(self):
        return reverse_lazy("portail_messagerie", kwargs={'idstructure': self.get_idstructure()})


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "portail/messagerie.html"
    texte_confirmation = _("Le message a bien été envoyé")
    titre_historique = "Ajouter un message"

    def Get_detail_historique(self, instance):
        return "Destinataire=%s Texte=%s" % (instance.structure, truncatechars(striptags(instance.texte), 40))

    def Apres_form_valid(self, form=None, instance=None):
        """ Envoie une notification de nouveau message à l'administrateur par email """
        try:
            # Vérifie qu'une notification doit être envoyée
            parametres_portail = utils_portail.Get_dict_parametres()
            if not parametres_portail.get("messagerie_envoyer_notification_admin", False):
                return

            # Importation de la structure concernée
            structure = Structure.objects.get(pk=self.get_idstructure())
            if not structure.adresse_exp:
                return
            url_message = self.request.build_absolute_uri(reverse_lazy("messagerie_portail", kwargs={"idstructure": structure.pk, "idfamille": self.request.user.famille.pk}))

            # Création du contenu du mail
            contenu_message = """
            <p>Bonjour,</p>
            <p>Vous avez reçu un nouveau message de <b>%s</b> sur le portail.</p>
            <p>Vous pouvez le consulter et y répondre en cliquant sur le lien suivant : <a href="%s" target="_blank">Accéder au message</a>.</p>
            <p>L'administrateur du portail</p>
            """ % (self.request.user.famille, url_message)

            # Création de l'email
            mail = Mail.objects.create(categorie="saisie_libre",
                objet="Nouveau message sur le portail",
                html=contenu_message,
                adresse_exp=structure.adresse_exp,
                utilisateur=self.request.user if self.request else None,
            )
            destinataire = Destinataire.objects.create(categorie="saisie_libre", adresse=structure.adresse_exp.adresse)
            mail.destinataires.add(destinataire)
            succes = utils_email.Envoyer_model_mail(idmail=mail.pk, request=self.request)
        except Exception as err:
            logger.error("Erreur dans l'envoi de la notification de message par email à l'amdinistrateur : %s" % err)
