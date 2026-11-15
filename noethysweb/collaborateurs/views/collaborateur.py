# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime, logging
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.db.models import Q, Exists, OuterRef, Prefetch
from django.views.generic.detail import DetailView
from django.contrib import messages
from django.utils.html import escape
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.views.base import CustomView
from core.models import Collaborateur, Note, ContratCollaborateur, TypeCongeCollaborateur, DemandeAbsenceCollaborateur, EvenementCollaborateur
from collaborateurs.forms.collaborateur import Formulaire
from collaborateurs.utils.utils_collaborateur import LISTE_ONGLETS, ONGLETS_SANS_MODIFICATION, Condition_contrat_en_cours, Situation_contrat, Ajouter_jetons_saisie_rapide
from collaborateurs.utils import utils_pieces_manquantes
from collaborateurs.utils import utils_conges, utils_objectif, utils_controle_reglementaire
logger = logging.getLogger(__name__)


def Peut_acceder_planning_individuel(user=None):
    # Import local : planning_individuel importe ce module
    from collaborateurs.views.planning_individuel import Peut_acceder
    return Peut_acceder(user)


class Page(crud.Page):
    model = Collaborateur
    menu_code = "collaborateur_liste"
    url_liste = "collaborateur_liste"
    url_ajouter = "collaborateur_ajouter"
    url_modifier = "collaborateur_resume"
    url_supprimer = "collaborateur_supprimer"
    description_liste = "Retrouvez ci-dessous les collaborateurs avec leur contrat en cours. Utilisez la liste déroulante pour afficher les collaborateurs en poste, ceux sans contrat en cours (anciens collaborateurs ou contrats à venir) ou tous les collaborateurs."
    description_saisie = "Saisissez toutes les informations concernant le collaborateur à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un collaborateur"
    objet_pluriel = "des collaborateurs"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


# Choix d'affichage de la liste des collaborateurs : (code, libellé)
CHOIX_SITUATION = [("", "Collaborateurs en poste"), ("sans_contrat", "Collaborateurs sans contrat en cours"), ("tous", "Tous les collaborateurs")]


class Liste(Page, crud.Liste):
    model = Collaborateur
    template_name = "core/crud/liste_avec_categorie.html"

    def Get_categorie(self):
        categorie = self.kwargs.get("categorie", "")
        return categorie if categorie in dict(CHOIX_SITUATION) else ""

    def get_queryset(self):
        conditions = (Q(groupes__superviseurs=self.request.user) | Q(groupes__superviseurs__isnull=True))
        en_cours = Exists(ContratCollaborateur.objects.filter(Condition_contrat_en_cours(prefixe=""), collaborateur=OuterRef("pk")))
        situation = {"": en_cours, "sans_contrat": ~en_cours, "tous": Q()}[self.Get_categorie()]
        contrats = Prefetch("contratcollaborateur_set", queryset=ContratCollaborateur.objects.select_related("type_contrat", "type_poste"))
        try:
            return Collaborateur.objects.filter(conditions, situation, self.Get_filtres("Q")).prefetch_related(contrats).distinct()
        except:
            return Collaborateur.objects.filter(conditions, situation).prefetch_related(contrats).distinct()

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['label_categorie'] = "Afficher"
        context['liste_categories'] = CHOIX_SITUATION
        context['categorie'] = self.Get_categorie()
        return context

    class datatable_class(MyDatatable):
        filtres = ["idcollaborateur", "nom", "prenom"]
        contrat = columns.TextColumn("Contrat", sources=None, processor='Get_contrat')
        poste = columns.TextColumn("Poste", sources=None, processor='Get_poste')
        echeance = columns.TextColumn("Période du contrat", sources=None, processor='Get_echeance')
        ville_resid = columns.TextColumn("Ville",  sources=None, processor='Get_ville_resid')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idcollaborateur", "nom", "prenom", "contrat", "poste", "echeance", "ville_resid"]
            ordering = ["nom", "prenom"]

        def Get_situation(self, instance):
            # Mémorisée sur l'instance pour les trois colonnes qui l'utilisent
            if not hasattr(instance, "_situation"):
                instance._situation = Situation_contrat(instance.contratcollaborateur_set.all())
            return instance._situation

        def Get_contrat(self, instance, *args, **kwargs):
            situation = self.Get_situation(instance)
            if situation["etat"] == "AUCUN":
                return "<span class='text-muted'>Aucun contrat</span>"
            contrat = situation["contrat"]
            nom = escape(contrat.type_contrat.nom) if contrat.type_contrat else "Contrat"
            if situation["etat"] == "A_VENIR":
                return "%s <span class='badge badge-info'>À venir</span>" % nom
            if situation["etat"] == "TERMINE":
                return "<span class='text-muted'>%s</span> <span class='badge badge-secondary'>Terminé</span>" % nom
            return nom

        def Get_poste(self, instance, *args, **kwargs):
            situation = self.Get_situation(instance)
            if not situation["contrat"]:
                return ""
            nom = escape(situation["contrat"].type_poste.nom)
            return "<span class='text-muted'>%s</span>" % nom if situation["etat"] == "TERMINE" else nom

        def Get_echeance(self, instance, *args, **kwargs):
            contrat = self.Get_situation(instance)["contrat"]
            if not contrat:
                return ""
            if not contrat.date_fin:
                return "Depuis le %s" % contrat.date_debut.strftime("%d/%m/%Y")
            return "Du %s au %s" % (contrat.date_debut.strftime("%d/%m/%Y"), contrat.date_fin.strftime("%d/%m/%Y"))

        def Get_ville_resid(self, instance, *args, **kwargs):
            return escape(instance.ville_resid or "")

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("collaborateur_resume", args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse("collaborateur_supprimer", args=[instance.pk])),
                # self.Create_bouton(url=reverse("famille_consommations", args=[instance.famille_id, instance.collaborateur_id]), title="Ouvrir la grille des consommations", icone="fa-calendar"),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire

    def get_success_url(self):
        """ Renvoie vers la page résumé du collaborateur """
        messages.add_message(self.request, messages.SUCCESS, "Ajout enregistré")
        return reverse_lazy("collaborateur_resume", kwargs={'idcollaborateur': self.object.idcollaborateur})


class Supprimer(Page, crud.Supprimer):
    pass

    def get_object(self):
        # Seuls les collaborateurs du périmètre de l'utilisateur peuvent être supprimés
        return get_object_or_404(Collaborateur.objects.filter(Q(groupes__superviseurs=self.request.user) | Q(groupes__superviseurs__isnull=True)).distinct(),
                                 pk=self.kwargs["idcollaborateur"])


# Pages de la fiche dont l'onglet ne se déduit pas du nom de l'URL : (code de l'onglet, modification)
DROITS_PAGES = {
    "collaborateur_notes_ajouter": ("resume", False),
    "collaborateur_notes_modifier": ("resume", False),
    "collaborateur_notes_supprimer": ("resume", False),
    "collaborateur_historique": ("outils", False),
    "collaborateur_emails_ajouter": ("outils", False),
    "collaborateur_sms_ajouter": ("outils", False),
    "collaborateur_voir_contrat": ("contrats", False),
    "collaborateur_appliquer_modele_planning": ("evenements", True),
}


class Onglet(CustomView):
    menu_code = "collaborateurs_toc"
    objet_singulier = "un collaborateur"
    liste_onglets = LISTE_ONGLETS

    def get_context_data(self, **kwargs):
        context = super(Onglet, self).get_context_data(**kwargs)
        context['page_titre'] = "Fiche collaborateur"
        context['liste_onglets'] = [dict_onglet for dict_onglet in self.liste_onglets if self.Onglet_autorise(dict_onglet["code"])]
        context['idcollaborateur'] = self.kwargs['idcollaborateur']
        context['collaborateur'] = Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])
        return context

    def Onglet_autorise(self, code="", modification=False):
        if code == "planning":
            # Le planning individuel dépend des permissions du planning (individuel ou général)
            return self.request.user.has_perm("core.planning_individuel") or self.request.user.has_perm("core.planning_equipe")
        if code == "conges":
            # Les congés dépendent des permissions des demandes d'absence et des compteurs de congés
            return self.request.user.has_perm("core.demandes_absences_collaborateurs") or self.request.user.has_perm("core.compteurs_conges_collaborateurs")
        if modification and code not in ONGLETS_SANS_MODIFICATION:
            return self.request.user.has_perm("core.collaborateur_%s_modifier" % code)
        return self.request.user.has_perm("core.collaborateur_%s" % code)

    def Get_droit_requis(self):
        """ Onglet et type d'accès (consultation ou modification) correspondant à la page demandée, déduits du nom de l'URL.
            Renvoie (None, False) pour une page inconnue : l'accès est alors refusé. """
        nom = self.request.resolver_match.url_name if self.request.resolver_match else ""
        if nom in DROITS_PAGES:
            return DROITS_PAGES[nom]
        reste = nom[len("collaborateur_"):] if nom.startswith("collaborateur_") else ""
        for code in sorted([onglet["code"] for onglet in LISTE_ONGLETS], key=len, reverse=True):
            if reste == code or reste.startswith(code + "_"):
                return code, reste[len(code):] not in ("", "_liste")
        return None, False

    def test_func_page(self):
        # Vérifie que l'utilisateur a la permission de consulter ou de modifier cet onglet
        code, modification = self.Get_droit_requis()
        if not code or not self.Onglet_autorise(code, modification):
            return False

        # Vérifie que l'utilisateur a une permission d'accéder à ce collaborateur
        idcollaborateur = self.Get_idcollaborateur()
        if idcollaborateur and not Collaborateur.objects.filter((Q(groupes__superviseurs=self.request.user) | Q(groupes__superviseurs__isnull=True)), pk=idcollaborateur).exists():
            return False
        return True

    def Get_idcollaborateur(self):
        return self.kwargs.get('idcollaborateur', None)


class Resume(Onglet, DetailView):
    template_name = "collaborateurs/collaborateur_resume.html"

    def get_context_data(self, **kwargs):
        context = super(Resume, self).get_context_data(**kwargs)
        context['box_titre'] = self.object.nom
        context['box_introduction'] = ""
        context['onglet_actif'] = "resume"

        # Alertes
        context['pieces_fournir'] = Ajouter_jetons_saisie_rapide(utils_pieces_manquantes.Get_pieces_manquantes(collaborateur=context["collaborateur"], only_invalides=True),
                                                                  user=self.request.user, collaborateur=context["collaborateur"])
        context['nbre_alertes'] = len(context['pieces_fournir'])

        # Synthèse : contrat, congés, solde d'heures, absences à venir, contrôle réglementaire
        context.update(self.Get_synthese(context["collaborateur"]))

        # Notes du collaborateur
        conditions = (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        context['notes'] = Note.objects.select_related("categorie").filter(conditions, collaborateur_id=self.kwargs['idcollaborateur']).order_by("date_saisie")

        return context

    def get_object(self):
        return Collaborateur.objects.get(pk=self.kwargs['idcollaborateur'])

    def Get_synthese(self, collaborateur=None):
        """ Informations de synthèse affichées sur le résumé. Chaque bloc est indépendant : une erreur n'empêche pas l'affichage de la fiche. """
        aujourdhui = datetime.date.today()
        user = self.request.user
        synthese = {}

        # Contrat en cours, à venir ou dernier contrat
        try:
            contrats = ContratCollaborateur.objects.select_related("type_contrat", "type_poste").filter(collaborateur=collaborateur)
            synthese["situation_contrat"] = Situation_contrat(contrats, aujourdhui)
        except Exception:
            logger.exception("Résumé collaborateur : contrat")

        # Soldes des compteurs de congés (période en cours)
        if utils_conges.Peut_acceder(user):
            try:
                types = [type_conge for type_conge in TypeCongeCollaborateur.objects.select_related("categorie").order_by("ordre", "nom") if type_conge.actif]
                compteurs = utils_conges.Get_compteurs([collaborateur.pk], types)
                synthese["soldes_conges"] = [dict(compteurs[(collaborateur.pk, type_conge.pk)], couleur=type_conge.categorie.couleur)
                                             for type_conge in types if compteurs[(collaborateur.pk, type_conge.pk)]["droits"] or compteurs[(collaborateur.pk, type_conge.pk)]["poses"]]
                synthese["demandes_attente"] = DemandeAbsenceCollaborateur.objects.filter(collaborateur=collaborateur, etat="ATTENTE").count()
            except Exception:
                logger.exception("Résumé collaborateur : congés")

        if Peut_acceder_planning_individuel(user):
            # Solde d'heures par rapport à l'objectif du contrat, à la date du jour
            try:
                parametres = utils_objectif.Get_parametres()
                type_periode = utils_objectif.Type_periode_defaut(idcollaborateur=collaborateur.pk, parametres=parametres, date=aujourdhui)
                periode = utils_objectif.Get_periode(utils_objectif.Annee_periode(aujourdhui, type_periode, parametres), type_periode, parametres)
                calcul = utils_objectif.Calcul_objectif(idcollaborateur=collaborateur.pk, periode=periode, parametres=parametres)
                if calcul.a_objectif:
                    solde = calcul.planifie_a_date - calcul.objectif_a_date
                    synthese["solde_heures"] = {"valeur": solde, "texte": ("+" if solde > 0.005 else "") + utils_objectif.Format_valeur(solde, calcul.unite),
                                                "periode": periode["libelle"]}
            except Exception:
                logger.exception("Résumé collaborateur : solde d'heures")

            # Alertes du contrôle réglementaire sur les 30 derniers jours et les 14 prochains
            try:
                anomalies = utils_controle_reglementaire.Get_anomalies(date_debut=aujourdhui - datetime.timedelta(days=30), date_fin=aujourdhui + datetime.timedelta(days=14),
                                                                         collaborateurs=[collaborateur.pk])
                for anomalie in anomalies:
                    anomalie["date_fr"] = datetime.datetime.strptime(anomalie["date"], "%Y-%m-%d").strftime("%d/%m/%Y")
                synthese["anomalies"] = sorted(anomalies, key=lambda anomalie: anomalie["date"], reverse=True)[:4]
                synthese["nbre_anomalies"] = len(anomalies)
            except Exception:
                logger.exception("Résumé collaborateur : contrôle réglementaire")

        # Absences à venir (60 prochains jours) : évènements des catégories de congés regroupés en périodes, et demandes en attente
        try:
            categories = {type_conge.categorie_id: type_conge.categorie for type_conge in TypeCongeCollaborateur.objects.select_related("categorie")}
            debut = datetime.datetime.combine(aujourdhui, datetime.time(0))
            fin = debut + datetime.timedelta(days=60)
            jours = {}
            for evenement in EvenementCollaborateur.objects.filter(collaborateur=collaborateur, type_evenement_id__in=categories.keys(), date_debut__lt=fin, date_fin__gt=debut):
                date = max(evenement.date_debut, debut).date()
                while date <= (min(evenement.date_fin, fin) - datetime.timedelta(minutes=1)).date():
                    jours.setdefault(evenement.type_evenement_id, set()).add(date)
                    date += datetime.timedelta(days=1)
            absences = []
            for idcategorie, dates in jours.items():
                dates = sorted(dates)
                bloc = [dates[0], dates[0]]
                for date in dates[1:] + [None]:
                    # Un week-end n'interrompt pas une période d'absence
                    if date and all((bloc[1] + datetime.timedelta(days=n)).weekday() >= 5 for n in range(1, (date - bloc[1]).days)):
                        bloc[1] = date
                        continue
                    absences.append({"debut": bloc[0], "fin": bloc[1], "nom": categories[idcategorie].nom, "couleur": categories[idcategorie].couleur, "attente": False})
                    if date:
                        bloc = [date, date]
            for demande in DemandeAbsenceCollaborateur.objects.select_related("type_conge__categorie").filter(collaborateur=collaborateur, etat="ATTENTE", date_fin__gte=aujourdhui):
                absences.append({"debut": demande.date_debut, "fin": demande.date_fin, "nom": demande.type_conge.nom, "couleur": demande.type_conge.categorie.couleur, "attente": True})
            synthese["absences"] = sorted(absences, key=lambda absence: absence["debut"])[:5]
        except Exception:
            logger.exception("Résumé collaborateur : absences à venir")

        return synthese
