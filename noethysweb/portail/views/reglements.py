# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
logger = logging.getLogger(__name__)
from django.http import JsonResponse
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
               "idmodele": idmodele, "idfamille": reglement.famille_id, "signataire": dict_options["signataire"],
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

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Règlements")
        context['liste_reglements'] = Reglement.objects.select_related("mode", "depot").filter(famille=self.request.user.famille).order_by("-date")
        return context
