# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.
import logging
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from portail.views.base import CustomView
from individus.utils import utils_pieces_manquantes
from portail.utils import utils_approbations
from core.models import PortailDocument, Inscription, Attestationdoc, Piece
from core.utils import utils_dates
import logging, datetime
logger = logging.getLogger(__name__)
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils.translation import gettext as _
from core.views import crud
from core.models import Consentement, Rattachement, Inscription, Famille, Information
from individus.utils import utils_vaccinations, utils_assurances
from portail.views.base import CustomView
from portail.forms.approbations import Formulaire
from django.shortcuts import render



class View(CustomView, crud.Modifier):
    menu_code = "portail_renseignements"
    form_class = Formulaire
    template_name = "portail/renseignements.html"
    mode = "CONSULTATION"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Renseignements")
        context['rattachements'] = Rattachement.objects.prefetch_related('individu').filter(famille=self.request.user.famille, individu__deces=False).order_by("individu__nom", "individu__prenom")
        # Ajout des traitements, alergies et dispenses à chaque individu
        for rattachement in context['rattachements']:
            individu = rattachement.individu
            
            # get traitements
            individu.traitements = Information.objects.filter(individu=individu).order_by("intitule")
            
            individu.allergies2 = individu.allergies.exclude(nom="RAS")
            
            individu.dispmed2 = individu.dispmed.all()
            
        #Recherche ID famille
        idfamille = self.request.user.famille
        familleid = Famille.objects.filter(nom=idfamille).values('idfamille').first()

        # Récupération des activités de la famille
        conditions = Q(famille=self.request.user.famille) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
        inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions)

        renseignements_manquants = {}

        # Recherche les informations manquantes
        for individu, liste_vaccinations in utils_vaccinations.Get_vaccins_obligatoires_by_inscriptions(inscriptions=inscriptions).items():
            renseignements_manquants.setdefault(individu, [])
            renseignements_manquants[individu].append("%d vaccination%s manquante%s" % (len(liste_vaccinations), "s" if len(liste_vaccinations) else "", "s" if len(liste_vaccinations) else ""))

        for individu in utils_assurances.Get_assurances_manquantes_by_inscriptions(famille=self.request.user.famille, inscriptions=inscriptions):
            renseignements_manquants.setdefault(individu, [])
            renseignements_manquants[individu].append("Assurance manquante")

        context["renseignements_manquants"] = renseignements_manquants
        context["familleid"] = familleid


        # Documents
        # Pièces à fournir
        context['pieces_fournir'] = utils_pieces_manquantes.Get_pieces_manquantes(
            famille=self.request.user.famille,
            exclure_individus=self.request.user.famille.individus_masques.all()
        )

        # Récupération des activités de la famille
        conditions = Q(famille=self.request.user.famille)
        inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions)
        activites = list({inscription.activite for inscription in inscriptions})

        # Importation des documents à télécharger
        liste_documents = []
        documents = PortailDocument.objects.filter(Q(activites__in=activites), activites__visible=True).order_by("titre").distinct()
        for document in documents:
            liste_documents.append({
                "titre": document.titre,
                "texte": document.texte,
                "fichier": document.document,
                "couleur_fond": document.couleur_fond,
                "extension": document.Get_extension()
            })
        for unite_consentement in utils_approbations.Get_approbations_requises(
                famille=self.request.user.famille,
                avec_consentements_existants=False
        ).get("consentements", []):
            liste_documents.append({
                "titre": unite_consentement.type_consentement.nom,
                "texte": "Version du %s" % utils_dates.ConvertDateToFR(unite_consentement.date_debut),
                "fichier": unite_consentement.document,
                "couleur_fond": "primary",
                "extension": unite_consentement.Get_extension()
            })
        context['liste_documents'] = liste_documents

        famille = self.request.user.famille
        # Récupérer les pièces de la famille ET des individus (pour gérer valide_rattachement)
        individus_famille = famille.rattachement_set.all().values_list('individu_id', flat=True)
        pieces = Piece.objects.filter(Q(famille=famille) | Q(individu__in=individus_famille))
        context['liste_pieces'] = pieces

        attestation = Attestationdoc.objects.filter(famille=famille)
        context['liste_attestations'] = attestation

        return context

    def get_object(self):
        return self.request.user.famille

    def get_success_url(self):
        return reverse_lazy("portail_renseignements")

    def form_valid(self, form):
        """ Enregistrement des approbations """
        # Enregistrement des approbations cochées
        nbre_coches = 0
        for code, coche in form.cleaned_data.items():
            if coche:
                if "unite" in code:
                    idunite = int(code.replace("unite_", ""))
                    Consentement.objects.create(famille=self.request.user.famille, unite_consentement_id=idunite)
                    nbre_coches += 1
                if "rattachement" in code:
                    idrattachement = int(code.replace("rattachement_", ""))
                    Rattachement.objects.filter(pk=idrattachement).update(certification_date=datetime.datetime.now())
                    nbre_coches += 1
                if "famille" in code:
                    self.request.user.famille.certification_date = datetime.datetime.now()
                    self.request.user.famille.save()
                    nbre_coches += 1

        # Message de confirmation
        if nbre_coches == 0:
            messages.add_message(self.request, messages.ERROR, _("Aucune approbation n'a été cochée"))
        elif nbre_coches == 1:
            messages.add_message(self.request, messages.SUCCESS, _("L'approbation cochée a bien été enregistrée"))
        else:
            messages.add_message(self.request, messages.SUCCESS, _("Les %d approbations cochées ont bien été enregistrées") % nbre_coches)
        return HttpResponseRedirect(self.get_success_url())


    def supprimer_piece(request, pk):
        piece = get_object_or_404(Piece, pk=pk)
        if request.method == 'POST':
            piece.delete()
            messages.success(request, 'La pièce a été supprimée avec succès.')
            return redirect('portail_renseignements')  # Redirigez vers la vue appropriée
        return render(request, 'core/confirmation_suppression.html', {'piece': piece})