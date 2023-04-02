# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic.detail import DetailView
from core.models import Collaborateur, ModeleSMS, SMS, DestinataireSMS
from collaborateurs.views.collaborateur import Onglet
from outils.forms.editeur_sms_express import Formulaire


class Ajouter(Onglet, DetailView):
    template_name = "collaborateurs/collaborateur_sms.html"

    def get_context_data(self, **kwargs):
        context = super(Ajouter, self).get_context_data(**kwargs)
        context['box_titre'] = "Envoyer un SMS"
        context['box_introduction'] = "Vous pouvez ici envoyer un SMS au collaborateur."
        context['onglet_actif'] = "outils"
        context['form'] = Formulaire(instance=self.Get_nouveau_sms(), request=self.request)
        context['modeles'] = ModeleSMS.objects.filter(categorie="saisie_libre")
        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])

    def Get_nouveau_sms(self):
        collaborateur = self.object

        # Création du SMS
        modele_sms = ModeleSMS.objects.filter(categorie="saisie_libre", defaut=True).first()
        sms = SMS.objects.create(
            objet=modele_sms.objet if modele_sms else "",
            texte=modele_sms.texte if modele_sms else "",
            configuration_sms=self.request.user.Get_configuration_sms_defaut(),
            selection="NON_ENVOYE",
            utilisateur=self.request.user,
        )

        # Création du destinataire
        destinataire = DestinataireSMS.objects.create(categorie="collaborateur", collaborateur=collaborateur, mobile=collaborateur.tel_mobile, valeurs={})
        sms.destinataires.add(destinataire)
        return sms
