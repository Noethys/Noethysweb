# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import HttpResponseRedirect
from django.contrib import messages
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from core.models import DestinataireSMS, SMS
from outils.views.editeur_sms import Page_destinataires


class Liste(Page_destinataires, TemplateView):
    template_name = "outils/editeur_sms_destinataires.html"
    categorie = "saisie_libre"

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['box_titre'] = "Saisie libre de numéros de téléphones"
        context['box_introduction'] = "Saisissez ci-dessous des numéros de téléphones séparés par des points-virgules."
        context['numeros'] = ";".join([destinataire.mobile for destinataire in DestinataireSMS.objects.filter(categorie="saisie_libre", sms=self.kwargs.get("idsms"))])
        return context

    def post(self, request, **kwargs):
        texte_numeros = request.POST.get("numeros")

        # Analyse les numéros
        liste_numeros = []
        if texte_numeros:
            for numero in texte_numeros.split(";"):
                liste_numeros.append(numero)

        # Importe le SMS
        sms = SMS.objects.get(pk=self.kwargs.get("idsms"))

        # Récupère la liste des listes de diffusion cochées
        liste_numeros_existants = [destinataire.mobile for destinataire in DestinataireSMS.objects.filter(categorie="saisie_libre", sms=sms)]

        # Recherche le dernier ID de la table Destinataires
        dernier_destinataire = DestinataireSMS.objects.last()
        idmax = dernier_destinataire.pk if dernier_destinataire else 0

        # Ajout des destinataires
        liste_ajouts = []
        for numero in liste_numeros:
            if numero not in liste_numeros_existants:
                liste_ajouts.append(DestinataireSMS(categorie="saisie_libre", mobile=numero))
        if liste_ajouts:
            # Enregistre les destinataires
            DestinataireSMS.objects.bulk_create(liste_ajouts)
            # Associe les destinataires au SMS
            destinataires = DestinataireSMS.objects.filter(pk__gt=idmax)
            ThroughModel = SMS.destinataires.through
            ThroughModel.objects.bulk_create([ThroughModel(sms_id=sms.pk, destinatairesms_id=destinataire.pk) for destinataire in destinataires])

        # Suppression des destinataires
        for numero in liste_numeros_existants:
            if numero not in liste_numeros:
                for destinataire in DestinataireSMS.objects.filter(categorie="saisie_libre", sms=sms):
                    if destinataire.mobile == numero:
                        destinataire.delete()

        return HttpResponseRedirect(reverse_lazy("editeur_sms", kwargs={'pk': sms.pk}))
