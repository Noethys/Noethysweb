# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.models import ListeDiffusion, Destinataire, Mail, Individu
from outils.views.editeur_emails import Page_destinataires
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.views.generic import TemplateView
import re


class Liste(Page_destinataires, TemplateView):
    template_name = "outils/editeur_emails_destinataires.html"
    categorie = "saisie_libre"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Saisie libre d'adresses emails"
        context['box_introduction'] = "Saisissez ci-dessous des adresses emails séparées par des points-virgules."
        context['adresses'] = ";".join([destinataire.adresse for destinataire in Destinataire.objects.filter(categorie="saisie_libre", mail=self.kwargs.get("idmail"))])
        return context

    def post(self, request, **kwargs):
        texte_adresses = request.POST.get("adresses")

        # Analyse les adresses
        liste_adresses = []
        if texte_adresses:
            liste_adresses = []

            # Vérifie toutes les adresses mails
            regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
            liste_anomalies = []
            for adresse in texte_adresses.split(";"):
                if not re.search(regex, adresse):
                    liste_anomalies.append(adresse)
                else:
                    liste_adresses.append(adresse)
            if liste_anomalies:
                messages.add_message(request, messages.ERROR, "Les adresses suivantes ne sont pas valides : %s" % ", ".join(liste_anomalies))

        # Importe le mail
        mail = Mail.objects.get(pk=self.kwargs.get("idmail"))

        # Récupère la liste des listes de diffusion cochées
        liste_adresses_existantes = [destinataire.adresse for destinataire in Destinataire.objects.filter(categorie="saisie_libre", mail=mail)]

        # Recherche le dernier ID de la table Destinataires
        dernier_destinataire = Destinataire.objects.last()
        idmax = dernier_destinataire.pk if dernier_destinataire else 0

        # Ajout des destinataires
        liste_ajouts = []
        for adresse in liste_adresses:
            if adresse not in liste_adresses_existantes:
                liste_ajouts.append(Destinataire(categorie="saisie_libre", adresse=adresse))
        if liste_ajouts:
            # Enregistre les destinataires
            Destinataire.objects.bulk_create(liste_ajouts)
            # Associe les destinataires au mail
            destinataires = Destinataire.objects.filter(pk__gt=idmax)
            ThroughModel = Mail.destinataires.through
            ThroughModel.objects.bulk_create([ThroughModel(mail_id=mail.pk, destinataire_id=destinataire.pk) for destinataire in destinataires])

        # Suppression des destinataires
        for adresse in liste_adresses_existantes:
            if adresse not in liste_adresses:
                destinataires = Destinataire.objects.filter(categorie="saisie_libre", adresse=adresse, mail=mail)
                destinataires.delete()

        return HttpResponseRedirect(reverse_lazy("editeur_emails", kwargs={'pk': mail.pk}))
