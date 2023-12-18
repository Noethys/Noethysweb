# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import json, datetime
from django.views.generic import TemplateView
from django.http import JsonResponse
from core.models import Reglement, Recu, ModeleEmail, ModeleImpression, Mail, Destinataire, DocumentJoint
from outils.utils import utils_email
from fiche_famille.views.famille import Onglet


def Envoyer_recu_automatiquement(request):
    # Récupération du règlement
    reglement = Reglement.objects.select_related("famille").get(pk=int(request.POST.get("idreglement")))

    # Numéro du reçu
    numero = 1
    dernier_recu = Recu.objects.last()
    if dernier_recu:
        numero = dernier_recu.numero + 1

    # Récupération du modèle d'impression
    modele_impression = ModeleImpression.objects.filter(categorie="reglement", defaut=True).first()
    if not modele_impression:
        return JsonResponse({"erreur": "Vous devez au préalable créer un modèle d'impression par défaut depuis le menu Paramétrage > Modèles d'impression"}, status=401)
    dict_options = json.loads(modele_impression.options)

    # Génération du reçu
    from fiche_famille.views.reglement_recu import Generer_recu
    resultat = Generer_recu(donnees={
        "idreglement": reglement.pk,
        "date_edition": datetime.date.today(),
        "numero": numero,
        "idmodele": modele_impression.modele_document_id,
        "idfamille": reglement.famille_id,
        "signataire": dict_options["signataire"],
        "intro": dict_options["intro"],
        "afficher_prestations": dict_options["afficher_prestations"]}
    )

    # Recherche de l'adresse d'expédition du mail
    adresse_exp = request.user.adresse_exp
    if not adresse_exp:
        return JsonResponse({"erreur": "Aucun modèle de document n'existe pour les règlements"}, status=401)

    # Création du mail
    modele_email = ModeleEmail.objects.filter(categorie="recu_reglement", defaut=True).first()
    if not modele_email:
        return JsonResponse({"erreur": "Aucun modèle d'emails pour les reçus de règlement n'a été paramétré"}, status=401)

    mail = Mail.objects.create(categorie="recu_reglement",
        objet=modele_email.objet if modele_email else "", html=modele_email.html if modele_email else "",
        adresse_exp=adresse_exp, selection="NON_ENVOYE", utilisateur=request.user if request else None)

    # Création du destinataire et de la pièce jointe
    destinataire = Destinataire.objects.create(categorie="famille", famille=reglement.famille, adresse=reglement.famille.mail, valeurs=json.dumps(resultat["champs"]))
    document_joint = DocumentJoint.objects.create(nom="Reçu de règlement", fichier=resultat["nom_fichier"])
    destinataire.documents.add(document_joint)
    mail.destinataires.add(destinataire)

    # Envoi du mail
    envois_reussis = utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)
    if envois_reussis:
        # Enregistrement du règlement
        Recu.objects.create(numero=numero, famille=reglement.famille, date_edition=datetime.date.today(), utilisateur=request.user, reglement=reglement)
        return JsonResponse({"succes": True})
    else:
        return JsonResponse({"erreur": "Erreur dans l'envoi de l'email"}, status=401)


class View(Onglet, TemplateView):
    template_name = "fiche_famille/reglement_recu_auto.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['box_titre'] = "Envoi d'un reçu"
        context['box_introduction'] = "Cette famille est abonnée à l'envoi des reçus de règlements par email. Confirmez-vous l'envoi du reçu ?"
        context['onglet_actif'] = "reglements"
        context['reglement'] = Reglement.objects.get(pk=kwargs["idreglement"])
        return context
