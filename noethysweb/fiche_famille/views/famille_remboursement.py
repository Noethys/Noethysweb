# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Prestation, Ventilation
from fiche_famille.forms.famille_remboursement import Formulaire
from fiche_famille.views.famille import Onglet
from facturation.utils import utils_factures
from reglements.utils import utils_ventilation
from core.utils import utils_preferences


class Ajouter(Onglet, crud.Ajouter):
    form_class = Formulaire
    template_name = "fiche_famille/famille_remboursement.html"

    def get_context_data(self, **kwargs):
        context = super(Ajouter, self).get_context_data(**kwargs)
        context['box_titre'] = "Rembourser le crédit de la famille"
        context['box_introduction'] = "Utilisez cette fonction lorsque la famille a payé plus que ce qui lui a été facturé et que vous lui rendez tout ou partie de ce crédit (chèque, virement, espèces...). Le remboursement est enregistré comme un règlement négatif."
        context['onglet_actif'] = "reglements"
        context['situation'] = context["form"].situation
        context['symbole_monnaie'] = utils_preferences.Get_symbole_monnaie()
        return context

    def get_success_url(self):
        return reverse_lazy("famille_reglements_liste", kwargs={'idfamille': self.kwargs.get('idfamille', None)})

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Ajouter, self).get_form_kwargs(**kwargs)
        form_kwargs["idfamille"] = self.Get_idfamille()
        return form_kwargs

    def form_valid(self, form):
        # Enregistrement du règlement négatif
        reglement = form.save(commit=True)
        label = "Remboursement du %s" % reglement.date.strftime("%d/%m/%Y")

        # Création de la prestation positive, ventilée automatiquement avec le crédit de la famille
        Prestation.objects.create(date=reglement.date, categorie="autre", label=label, famille=reglement.famille,
                                  montant_initial=-reglement.montant, montant=-reglement.montant)
        utils_ventilation.Ventilation_auto(IDfamille=reglement.famille_id)

        # Création de la prestation négative, ventilée avec le règlement négatif
        prestation_negative = Prestation.objects.create(date=reglement.date, categorie="autre", label=label, famille=reglement.famille,
                                                        montant_initial=reglement.montant, montant=reglement.montant)
        Ventilation.objects.create(famille=reglement.famille, reglement=reglement, prestation=prestation_negative, montant=reglement.montant)

        # Recalcule le solde des factures de la famille
        utils_factures.Maj_solde_actuel_factures(IDfamille=reglement.famille_id)

        return super().form_valid(form)
