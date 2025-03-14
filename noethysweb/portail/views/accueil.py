# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from django.db.models import Q
from portail.views.base import CustomView
from portail.utils import utils_approbations
from individus.utils import utils_pieces_manquantes, utils_vaccinations, utils_assurances
from cotisations.utils import utils_cotisations_manquantes
from core.models import PortailMessage, Article, Inscription, Consommation, Lecture
from core.models import Rattachement
from portail.utils import utils_champs


class Accueil(CustomView, TemplateView):
    template_name = "portail/accueil.html"
    menu_code = "portail_accueil"

    def get_famille_object(self):
        if hasattr(self.request.user, 'famille'):
            return [self.request.user.famille]
        elif hasattr(self.request.user, 'individu'):
            # Récupérer toutes les familles auxquelles l'individu est rattaché
            rattachements = Rattachement.objects.filter(individu=self.request.user.individu)
            return [rattachement.famille for rattachement in rattachements if rattachement.famille and rattachement.titulaire == 1]
        return []

    def get_context_data(self, **kwargs):
        context = super(Accueil, self).get_context_data(**kwargs)
        context['page_titre'] = _("Accueil")

        # Obtenez la liste des familles
        familles = self.get_famille_object()

        # Transférer les familles au contexte
        context['familles'] = familles

        # Initialiser un dictionnaire pour contenir les attachements et les inscriptions de toutes les familles
        context['rattachements'] = []
        renseignements_manquants = {}

        # Variables pour accumuler les totaux
        total_pieces_manquantes = 0
        total_informations_manquantes = 0
        total_messages_non_lus = 0
        total_approbations_requises = 0
        total_vaccinations_manquantes = 0
        total_assurances_manquantes = 0
        total_cotisations_manquantes = []

        for famille in familles:
            # Récupérer les rattachements (individus) pour chaque famille
            rattachements = Rattachement.objects.prefetch_related('famille', 'individu').filter(
                famille=famille,
                individu__deces=False
            ).order_by("individu__nom", "individu__prenom")

            context['rattachements'].extend(rattachements)  # Ajoutez les rattachements de cette famille au contexte

            # Si famille n'est pas trouvée, nous sortons pour éviter les erreurs
            if not famille:
                return context
            # Informations manquantes
            nbre_informations_manquantes= utils_champs.Get_renseignements_manquants(famille=famille)["NBRE"]
            total_informations_manquantes += nbre_informations_manquantes
            # Pièces manquantes
            pieces_manquantes = len(utils_pieces_manquantes.Get_pieces_manquantes(famille=famille, only_invalides=True,
                                                                                  exclure_individus=famille.individus_masques.all()))
            total_pieces_manquantes += pieces_manquantes

            # On construit le filtre conditionnel selon la catégorie de l'utilisateur
            if self.request.user.categorie == "individu" and hasattr(self.request.user, "individu"):
                extra_filter = Q(individu=self.request.user.individu) | Q(individu__isnull=True)
            elif self.request.user.categorie == "famille" and hasattr(self.request.user, "famille"):
                extra_filter = Q(famille=self.request.user.famille) | Q(famille__isnull=True)
            else:
                # En cas d'inattendu, on peut choisir d'appliquer aucun filtre ou de lever une exception
                extra_filter = Q()

            # Application du filtre sur les messages non lus
            messages_non_lus = PortailMessage.objects.filter(
                Q(famille__in=familles),
                Q(utilisateur__isnull=False),
                Q(date_lecture__isnull=True),
                extra_filter
            ).exclude(utilisateur=self.request.user).count()

            # Approbations
            approbations_requises = utils_approbations.Get_approbations_requises(famille=famille)
            total_approbations_requises += approbations_requises["nbre_total"]

            # Récupération des activités de la famille
            conditions = Q(famille=famille) & (Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.date.today()))
            inscriptions = Inscription.objects.select_related("activite", "individu").filter(conditions)
            activites = list({inscription.activite: True for inscription in inscriptions}.keys())

            # Vaccins manquants
            vaccinations_manquantes = sum([len(liste_vaccinations) for individu, liste_vaccinations in
                                           utils_vaccinations.Get_vaccins_obligatoires_by_inscriptions(
                                               inscriptions=inscriptions).items()])
            total_vaccinations_manquantes += vaccinations_manquantes

            # Assurances manquantes
            assurances_manquantes = len(
                utils_assurances.Get_assurances_manquantes_by_inscriptions(famille=famille, inscriptions=inscriptions))
            total_assurances_manquantes += assurances_manquantes

            # Adhésions manquantes
            if context["parametres_portail"].get("cotisations_afficher_page", False):
                cotisations_manquantes = utils_cotisations_manquantes.Get_cotisations_manquantes(famille=famille,
                                                                                                 exclure_individus=famille.individus_masques.all())
                total_cotisations_manquantes.extend(cotisations_manquantes)

            # Articles
            conditions = Q(statut="publie") & Q(date_debut__lte=datetime.datetime.now()) & (
                        Q(date_fin__isnull=True) | Q(date_fin__gte=datetime.datetime.now()))
            conditions &= (Q(public__in=("toutes", "presents", "presents_groupes")) | (
                        Q(public="inscrits") & Q(activites__in=activites)))
            articles = Article.objects.select_related("image_article", "album", "sondage", "auteur").filter(
                conditions).distinct().order_by("-date_debut")
            selection_articles = []
            popups = []
            for article in articles:
                # Filtre les présents si besoin
                if article.public in ("presents", "presents_groupes"):
                    conditions = Q(inscription__famille=famille, date__gte=article.present_debut,
                                   date__lte=article.present_fin, etat__in=("reservation", "present"))
                    if article.public == "presents":
                        conditions &= Q(activite__in=article.activites.all())
                    if article.public == "presents_groupes":
                        conditions &= Q(groupe__in=article.groupes.all())
                    valide = Consommation.objects.filter(conditions).exists()
                else:
                    valide = True
                if valide:
                    selection_articles.append(article)
                    if article.texte_popup:
                        popups.append(article)
            context['articles'] = selection_articles

            # Popups
            context['articles_popups'] = []
            if popups:
                popups_lus = [lecture.article for lecture in
                              Lecture.objects.filter(article__in=popups, famille=famille)]
                for popup in popups:
                    if popup not in popups_lus:
                        context['articles_popups'].append(popup)
                        Lecture.objects.create(famille=famille, article=popup)

        # Ajouter les totaux dans le contexte
        context['nbre_pieces_manquantes'] = total_pieces_manquantes
        context['nbre_informations_manquantes'] = total_informations_manquantes
        context['nbre_messages_non_lus'] = messages_non_lus
        context['nbre_approbations_requises'] = total_approbations_requises
        context["nbre_vaccinations_manquantes"] = total_vaccinations_manquantes
        context["nbre_assurances_manquantes"] = total_assurances_manquantes
        context["cotisations_manquantes"] = total_cotisations_manquantes

        return context