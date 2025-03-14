# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
from core.models import Rattachement
logger = logging.getLogger(__name__)
from django.http import JsonResponse, Http404
from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from core.models import Reglement, ModeleImpression, Recu
from portail.views.base import CustomView


def imprimer_recu(request):
    """ Imprimer un reçu de règlement au format PDF """
    idreglement = int(request.POST.get("idreglement", 0))
    idmodele = int(request.POST.get("idmodele_impression", 0))

    # Importation des options d'impression
    modele_impression = ModeleImpression.objects.get(pk=idmodele)
    dict_options = json.loads(modele_impression.options)
    dict_options["modele"] = modele_impression.modele_document

    # Importation du règlement
    reglement = Reglement.objects.get(pk=idreglement, famille=request.user.famille)

    # Création du numéro de reçu
    numero = 1
    dernier_recu = Recu.objects.last()
    if dernier_recu:
        numero = dernier_recu.numero + 1

    # Création du PDF
    donnees = {"idreglement": reglement.pk, "date_edition": datetime.date.today(), "numero": numero,
               "idmodele": modele_impression.modele_document_id, "idfamille": reglement.famille_id, "signataire": dict_options["signataire"],
               "intro": dict_options["intro"], "afficher_prestations": dict_options["afficher_prestations"]}

    # Mémorisation du reçu
    Recu.objects.create(numero=numero, famille_id=reglement.famille_id, date_edition=donnees["date_edition"],
                        reglement=reglement, utilisateur=request.user)

    from fiche_famille.views.reglement_recu import Generer_recu
    resultat = Generer_recu(donnees=donnees)
    return JsonResponse(resultat)


class View(CustomView, TemplateView):
    menu_code = "portail_reglements"
    template_name = "portail/reglements.html"

    def get_object(self):
        """Récupérer l'objet famille ou individu selon l'utilisateur"""
        if hasattr(self.request.user, 'famille'):
            return self.request.user.famille
        elif hasattr(self.request.user, 'individu'):
            return self.request.user.individu
        else:
            raise Http404("Utilisateur non reconnu.")

    def get_famille_object(self):
        """Récupérer les familles de l'individu si applicable"""
        if hasattr(self.request.user, 'famille'):
            return [self.request.user.famille]
        elif hasattr(self.request.user, 'individu'):
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            familles = [rattachement.famille for rattachement in rattachements if rattachement.famille and rattachement.titulaire == 1]
            return familles if familles else None
        return None

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Règlements")
        familles = self.get_famille_object()

        if familles:
                # Fetch all regulations linked to these families
                liste_reglements = Reglement.objects.select_related("mode", "depot").filter(famille__in=familles).order_by("-date")

                # Grouping by family name
                reglements_grouped = {}
                for reglement in liste_reglements:
                    famille_nom = reglement.famille.nom  # Adjust this based on your actual model structure
                    if famille_nom not in reglements_grouped:
                        reglements_grouped[famille_nom] = []
                    reglements_grouped[famille_nom].append(reglement)

                context['reglements_grouped'] = reglements_grouped
        return context