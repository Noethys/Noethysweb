# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, random, datetime, json
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.core.cache import cache
from django.conf import settings
from django.db.models import Count, Q
from core.views.base import CustomView
from core.data.data_citations import LISTE_CITATIONS
from core.data.data_celebrations import DICT_FETES, DICT_CELEBRATIONS
from core.models import Individu, Note, Consommation, Ouverture, Activite
from core.utils import utils_parametres, utils_texte
from consommations.views import suivi_consommations
from individus.views import suivi_inscriptions
from outils.utils import utils_update


class Accueil(CustomView, TemplateView):
    template_name = "core/accueil/accueil.html"
    menu_code = "accueil"

    def get_context_data(self, **kwargs):
        context = super(Accueil, self).get_context_data(**kwargs)
        context['page_titre'] = "Accueil"

        # Suivi des conso et des inscriptions
        context['suivi_consommations_parametres'] = suivi_consommations.Get_parametres(request=self.request)
        context['suivi_inscriptions_parametres'] = suivi_inscriptions.Get_parametres(request=self.request)

        # Technique
        context['mode_demo'] = settings.MODE_DEMO
        context['nouvelle_version'] = self.Get_update()

        # Ephéméride
        context['citation_texte'], context['citation_auteur'] = self.Get_citation()
        context['celebrations'] = self.Get_celebrations()
        context['anniversaires_aujourdhui'] = self.Get_anniversaires()
        context['anniversaires_demain'] = self.Get_anniversaires(demain=True)

        # Graphique nombre d'individus
        context['graphique_individus_activite'] = utils_parametres.Get(nom="activite", categorie="graphique_individus", utilisateur=self.request.user, valeur=0)
        context['graphique_individus'] = self.Get_graphique_individu(idactivite=context['graphique_individus_activite'])

        # Notes
        conditions = Q(date_parution__lte=datetime.date.today()) & (Q(utilisateur=self.request.user) | Q(utilisateur__isnull=True)) & (Q(structure__in=self.request.user.structures.all()) | Q(structure__isnull=True))
        context['notes'] = Note.objects.select_related('famille', 'individu').filter(conditions, afficher_accueil=True).order_by("date_parution")
        return context

    def Get_update(self):
        """ Recherche si une nouvelle version est disponible """
        key_cache = "last_check_update_user%d" % self.request.user.pk
        last_check_update = cache.get(key_cache)
        if last_check_update:
            nouvelle_version = last_check_update["nouvelle_version"]
            # Si la dernière recherche date de plus d'un jour, on cherche une nouvelle version
            if datetime.date.today() > last_check_update["date"].date():
                last_check_update = None
        if not last_check_update:
            logger.debug("Recherche d'une nouvelle version...")
            nouvelle_version, changelog = utils_update.Recherche_update()
            cache.set(key_cache, {"date": datetime.datetime.now(), "nouvelle_version": nouvelle_version})
        return nouvelle_version

    def Get_citation(self):
        num_citation = cache.get('num_citation')
        if not num_citation:
            parametre = utils_parametres.Get(nom="num_citation", categorie="page_accueil", valeur="")
            if parametre.startswith(str(datetime.date.today())):
                num_citation = int(parametre.split(";")[1])
            else:
                num_citation = random.randint(0, len(LISTE_CITATIONS) - 1)
                utils_parametres.Set(nom="num_citation", categorie="page_accueil", valeur="%s;%d" % (datetime.date.today(), num_citation))
            cache.set('num_citation', num_citation)
        return LISTE_CITATIONS[num_citation]

    def Get_celebrations(self):
        """ Récupère les célébrations du jour """
        date_jour = datetime.date.today()

        # Fêtes
        texte_fetes = ""
        if (date_jour.day, date_jour.month) in DICT_FETES:
            noms = DICT_FETES[(date_jour.day, date_jour.month)]
            texte_fetes = utils_texte.Convert_liste_to_texte_virgules(noms.split(";"))

        # Célébrations
        texte_celebrations = ""
        if (date_jour.day, date_jour.month) in DICT_CELEBRATIONS:
            texte_celebrations = DICT_CELEBRATIONS[(date_jour.day, date_jour.month)]

        # Mix des fêtes et des célébrations
        if texte_fetes and texte_celebrations: return "Nous fêtons aujourd'hui les %s et célébrons %s." % (texte_fetes, texte_celebrations)
        elif texte_fetes and not texte_celebrations: return "Nous fêtons aujourd'hui les %s." % texte_fetes
        elif not texte_fetes and texte_celebrations: return "Nous célébrons aujourd'hui %s." % texte_celebrations
        return "Aucune célébration aujourd'hui."

    def Get_anniversaires(self, demain=False):
        """ Récupère les anniversaires """
        texte_anniversaires = cache.get("texte_anniversaires_demain" if demain else "texte_anniversaires")
        if not texte_anniversaires:
            date_jour = datetime.date.today()
            if demain:
                date_jour += datetime.timedelta(days=1)
            # individus = Individu.objects.filter(date_naiss__month=date_jour.month, date_naiss__day=date_jour.day, inscription__isnull=False).distinct()
            individus = Individu.objects.filter(date_naiss__isnull=False, inscription__isnull=False).distinct()
            liste_textes = []
            for individu in individus:
                if individu.date_naiss.month == date_jour.month and individu.date_naiss.day == date_jour.day:
                    liste_textes.append("%s %s (%d ans)" % (individu.prenom, individu.nom, individu.Get_age(today=date_jour)))
            if liste_textes:
                texte_anniversaires = "Joyeux anniversaire à %s." % utils_texte.Convert_liste_to_texte_virgules(liste_textes)
            else:
                texte_anniversaires = "Aucun anniversaire à fêter."
            cache.set("texte_anniversaires_demain" if demain else "texte_anniversaires", texte_anniversaires, timeout=30)
        return texte_anniversaires

    def Get_graphique_individu(self, idactivite=0):
        conditions = Q(activite_id=idactivite) & Q(date__gte=datetime.date.today() - datetime.timedelta(days=10)) & Q(date__lte=datetime.date.today() + datetime.timedelta(days=30))
        liste_ouvertures = Ouverture.objects.values("date").filter(conditions).distinct().order_by("date")
        consommations = {item["date"]: item["nbre"] for item in Consommation.objects.values("date").filter(conditions, etat__in=("reservation", "present")).annotate(nbre=Count("individu_id"))}
        liste_labels, liste_valeurs = [], []
        for ouverture in liste_ouvertures:
            liste_labels.append(str(ouverture["date"]))
            liste_valeurs.append(consommations.get(ouverture["date"], 0))
        return {"labels": json.dumps(liste_labels), "valeurs": json.dumps(liste_valeurs)}
