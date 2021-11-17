# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.db.models import Q
from django.views.generic.detail import DetailView
from core.models import Famille, ModeleEmail, Mail, SignatureEmail, Destinataire
from fiche_famille.views.famille import Onglet
from outils.forms.editeur_emails_express import Formulaire


class Ajouter(Onglet, DetailView):
    template_name = "fiche_famille/famille_emails.html"

    def get_context_data(self, **kwargs):
        context = super(Ajouter, self).get_context_data(**kwargs)
        context['box_titre'] = "Envoyer un Email"
        context['box_introduction'] = "Vous pouvez ici envoyer un Email à la famille."
        context['onglet_actif'] = "outils"
        context['form'] = Formulaire(instance=self.Get_nouveau_mail(), request=self.request)
        context['modeles'] = ModeleEmail.objects.filter(categorie="saisie_libre")
        context['signatures'] = SignatureEmail.objects.filter(Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        return context

    def get_object(self):
        return Famille.objects.get(pk=self.kwargs['idfamille'])

    def Get_nouveau_mail(self):
        famille = self.object

        # Création du mail
        modele_email = ModeleEmail.objects.filter(categorie="saisie_libre", defaut=True).first()
        mail = Mail.objects.create(
            categorie="saisie_libre",
            objet=modele_email.objet if modele_email else "",
            html=modele_email.html if modele_email else "",
            adresse_exp=self.request.user.Get_adresse_exp_defaut(),
            selection="NON_ENVOYE",
            verrouillage_destinataires=True,
            utilisateur=self.request.user,
        )

        # Création du destinataire et du document joint
        destinataire = Destinataire.objects.create(categorie="famille", famille=famille, adresse=famille.mail, valeurs={})
        mail.destinataires.add(destinataire)
        return mail
