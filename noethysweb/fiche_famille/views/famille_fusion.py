# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Fusion des fiches familles et des fiches individuelles saisies en double """

import logging
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from core.models import Famille, Individu, Rattachement
from fiche_famille.views.famille import Onglet
from fiche_famille.forms.famille_fusion import Formulaire_selection_famille, Formulaire_selection_individu
from fiche_famille.utils import utils_fusion

logger = logging.getLogger(__name__)


def Retirer_historique_recherche(request, idfamille):
    """ Retire une famille supprimée de l'historique des recherches """
    historique = request.session.get("historique_recherche", [])
    nouvel_historique = [dict_historique for dict_historique in historique if dict_historique.get("idfamille") != idfamille]
    if len(nouvel_historique) != len(historique):
        request.session["historique_recherche"] = nouvel_historique
        request.session.modified = True


def Get_entier(valeur):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def Get_conditions_recherche(terme, champs):
    """ Chaque mot saisi doit figurer dans l'un des champs ; un nombre (ou 'ID12') recherche aussi l'ID """
    conditions = Q()
    for mot in terme.replace(",", " ").split():
        condition_mot = Q()
        for champ in champs:
            condition_mot |= Q(**{"%s__icontains" % champ: mot})
        idobjet = Get_entier(mot[2:] if mot.lower().startswith("id") else mot)
        if idobjet:
            condition_mot |= Q(pk=idobjet)
        conditions &= condition_mot
    return conditions


def Rechercher_individus(request):
    """ Recherche AJAX des individus pour le Select2 de la fusion d'individus """
    if not utils_fusion.Autorise(request.user):
        return HttpResponseForbidden()
    terme = request.GET.get("term", "").strip()
    resultats = []
    if len(terme) >= 2:
        for individu in Individu.objects.filter(Get_conditions_recherche(terme, ["nom", "prenom", "nom_jfille"])).order_by("nom", "prenom")[:30]:
            date_naiss = " - né(e) le %s" % individu.date_naiss.strftime("%d/%m/%Y") if individu.date_naiss else ""
            resultats.append({"id": individu.pk, "text": "%s (ID%d)%s" % (individu.Get_nom(), individu.pk, date_naiss)})
    return JsonResponse({"results": resultats})


def Rechercher_familles(request):
    """ Recherche AJAX des familles pour le Select2 de la fusion de familles """
    if not utils_fusion.Autorise(request.user):
        return HttpResponseForbidden()
    terme = request.GET.get("term", "").strip()
    resultats = []
    if len(terme) >= 2:
        familles = Famille.objects.filter(Get_conditions_recherche(terme, ["nom"])).exclude(pk=Get_entier(request.GET.get("exclure")) or 0).order_by("nom")[:30]
        for famille in familles:
            resultats.append({"id": famille.pk, "text": "%s (ID%d)%s" % (famille.nom or "Famille sans nom", famille.pk, " - %s" % famille.ville_resid if famille.ville_resid else "")})
    return JsonResponse({"results": resultats})


class Page(Onglet, TemplateView):
    compatible_demo = False

    def test_func_page(self):
        return utils_fusion.Autorise(self.request.user)

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['onglet_actif'] = "outils"
        return context

    def Erreur(self, texte, **params):
        messages.add_message(self.request, messages.ERROR, texte)
        url = reverse(self.url_name, kwargs={"idfamille": self.kwargs["idfamille"]})
        if params:
            url += "?" + "&".join("%s=%s" % (cle, valeur) for cle, valeur in params.items())
        return redirect(url)

    def Afficher_rapport(self, rapport, texte_succes):
        messages.add_message(self.request, messages.SUCCESS, texte_succes)
        for avertissement in rapport.avertissements:
            messages.add_message(self.request, messages.WARNING, avertissement)


class Fusion_familles(Page):
    template_name = "fiche_famille/famille_fusion.html"
    url_name = "famille_fusion"

    def get(self, request, *args, **kwargs):
        self.famille_doublon = None
        iddoublon = Get_entier(request.GET.get("famille"))
        if "famille" in request.GET and not iddoublon:
            return self.Erreur("Veuillez rechercher et sélectionner la famille en double.")
        if iddoublon:
            self.famille_doublon = Famille.objects.filter(pk=iddoublon).first()
            if not self.famille_doublon or iddoublon == self.kwargs["idfamille"]:
                return self.Erreur("Veuillez sélectionner une autre famille.")
        return super(Fusion_familles, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(Fusion_familles, self).get_context_data(**kwargs)
        context['box_titre'] = "Fusionner avec une autre famille"
        famille = context['famille']

        # Étape 1 : sélection de la famille en double
        if not self.famille_doublon:
            context['etape'] = "selection"
            context['box_introduction'] = "Sélectionnez la fiche famille saisie en double. Toutes ses données seront transférées dans cette fiche, puis elle sera supprimée. Rien n'est modifié avant la confirmation."
            context['form'] = Formulaire_selection_famille(idfamille=famille.pk)
            context['suggestions'] = self.Get_suggestions(famille)
            return context

        # Étape 2 : analyse et rapprochement des individus
        context['etape'] = "analyse"
        context['box_introduction'] = "Vérifiez les individus à fusionner puis confirmez. La fiche de gauche sera supprimée après le transfert de toutes ses données dans la fiche de droite."
        context['famille_doublon'] = self.famille_doublon
        context.update(utils_fusion.Analyser_fusion_familles(famille_garde=famille, famille_doublon=self.famille_doublon))
        return context

    def Get_suggestions(self, famille):
        """ Familles comportant un homonyme d'un membre de cette famille """
        suggestions = {}
        for individu in utils_fusion.Get_individus_famille(famille):
            for homonyme in utils_fusion.Rechercher_homonymes(individu):
                for rattachement in Rattachement.objects.select_related("famille").filter(individu=homonyme).exclude(famille=famille):
                    suggestion = suggestions.setdefault(rattachement.famille_id, {"famille": rattachement.famille, "individus": []})
                    if homonyme.Get_nom() not in suggestion["individus"]:
                        suggestion["individus"].append(homonyme.Get_nom())
        return sorted(suggestions.values(), key=lambda suggestion: -len(suggestion["individus"]))[:10]

    def post(self, request, *args, **kwargs):
        famille = Famille.objects.get(pk=self.kwargs["idfamille"])
        famille_doublon = Famille.objects.filter(pk=Get_entier(request.POST.get("famille_doublon"))).first()
        if not famille_doublon:
            return self.Erreur("La famille en double n'existe plus.")
        if not request.POST.get("confirmation"):
            return self.Erreur("Veuillez cocher la case de confirmation.", famille=famille_doublon.pk)

        # Correspondances des individus à fusionner
        correspondances = {}
        for rattachement in Rattachement.objects.filter(famille=famille_doublon):
            idgarde = Get_entier(request.POST.get("individu_%d" % rattachement.individu_id))
            if idgarde:
                correspondances[rattachement.individu_id] = idgarde

        try:
            rapport = utils_fusion.Fusionner_familles(famille_garde=famille, famille_doublon=famille_doublon, correspondances=correspondances, utilisateur=request.user)
        except utils_fusion.Erreur_fusion as err:
            return self.Erreur(str(err), famille=famille_doublon.pk)
        except Exception:
            logger.exception("Erreur lors de la fusion des familles %s et %s", famille.pk, famille_doublon.pk)
            return self.Erreur("La fusion a échoué à cause d'une erreur technique et aucune donnée n'a été modifiée. Le détail a été enregistré dans le journal de l'application.", famille=famille_doublon.pk)

        Retirer_historique_recherche(request, famille_doublon.pk)
        self.Afficher_rapport(rapport, "La fusion des familles a été effectuée. Le détail est consultable dans l'historique de la famille.")
        return redirect("famille_resume", idfamille=famille.pk)


class Fusion_individus(Page):
    template_name = "fiche_famille/famille_fusion_individus.html"
    url_name = "famille_fusion_individus"

    def get(self, request, *args, **kwargs):
        self.individu_garde, self.individu_doublon = None, None
        idgarde, iddoublon = Get_entier(request.GET.get("garde")), Get_entier(request.GET.get("doublon"))
        if "garde" in request.GET or "doublon" in request.GET:
            if not idgarde:
                return self.Erreur("Veuillez cocher la fiche à conserver.")
            if not iddoublon:
                return self.Erreur("Veuillez rechercher et sélectionner la fiche en double.")
        if idgarde and iddoublon:
            if not Rattachement.objects.filter(famille_id=self.kwargs["idfamille"], individu_id=idgarde).exists():
                return self.Erreur("L'individu conservé doit être un membre de cette famille.")
            self.individu_garde = Individu.objects.filter(pk=idgarde).first()
            self.individu_doublon = Individu.objects.filter(pk=iddoublon).first()
            if not self.individu_garde or not self.individu_doublon or idgarde == iddoublon:
                return self.Erreur("Veuillez sélectionner deux individus différents.")
        return super(Fusion_individus, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(Fusion_individus, self).get_context_data(**kwargs)
        context['box_titre'] = "Fusionner un individu en double"
        famille = context['famille']

        # Étape 1 : sélection des individus
        if not self.individu_garde:
            context['etape'] = "selection"
            context['box_introduction'] = "Sélectionnez la fiche individuelle à conserver puis sa fiche en double, qui peut se trouver dans cette famille ou dans une autre. Toutes les données de la fiche en double seront transférées, puis elle sera supprimée."
            membres = utils_fusion.Get_individus_famille(famille)
            context['membres'] = membres
            context['form'] = Formulaire_selection_individu()
            context['suggestions'] = self.Get_suggestions(membres)
            return context

        # Étape 2 : analyse
        context['etape'] = "analyse"
        context['box_introduction'] = "Vérifiez les informations puis confirmez. La fiche de gauche sera supprimée après le transfert de toutes ses données dans la fiche de droite."
        context['individu_garde'] = self.individu_garde
        context['individu_doublon'] = self.individu_doublon
        context['inversion_possible'] = Rattachement.objects.filter(famille=famille, individu=self.individu_doublon).exists()
        context.update(utils_fusion.Analyser_fusion_individus(individu_garde=self.individu_garde, individu_doublon=self.individu_doublon))
        return context

    def Get_suggestions(self, membres):
        """ Doublons probables : homonymes dans la famille ou dans la base """
        suggestions, deja_vus = [], set()
        for membre in membres:
            for homonyme in utils_fusion.Rechercher_homonymes(membre):
                cle = tuple(sorted((membre.pk, homonyme.pk)))
                if cle in deja_vus:
                    continue
                deja_vus.add(cle)
                rattachement = Rattachement.objects.select_related("famille").filter(individu=homonyme).first()
                suggestions.append({"garde": membre, "doublon": homonyme, "score": utils_fusion.Score_ressemblance(membre, homonyme),
                                    "famille": rattachement.famille if rattachement else None})
        return suggestions

    def post(self, request, *args, **kwargs):
        idgarde, iddoublon = Get_entier(request.POST.get("individu_garde")), Get_entier(request.POST.get("individu_doublon"))
        individu_garde = Individu.objects.filter(pk=idgarde).first()
        individu_doublon = Individu.objects.filter(pk=iddoublon).first()
        if not individu_garde or not individu_doublon or not Rattachement.objects.filter(famille_id=self.kwargs["idfamille"], individu=individu_garde).exists():
            return self.Erreur("Les individus sélectionnés ne sont pas valides.")
        if not request.POST.get("confirmation"):
            return self.Erreur("Veuillez cocher la case de confirmation.", garde=idgarde, doublon=iddoublon)

        familles_doublon = set(Rattachement.objects.filter(individu=individu_doublon).values_list("famille_id", flat=True))
        try:
            rapport = utils_fusion.Fusionner_individus(individu_garde=individu_garde, individu_doublon=individu_doublon, utilisateur=request.user)
        except utils_fusion.Erreur_fusion as err:
            return self.Erreur(str(err), garde=idgarde, doublon=iddoublon)
        except Exception:
            logger.exception("Erreur lors de la fusion des individus %s et %s", idgarde, iddoublon)
            return self.Erreur("La fusion a échoué à cause d'une erreur technique et aucune donnée n'a été modifiée. Le détail a été enregistré dans le journal de l'application.", garde=idgarde, doublon=iddoublon)

        self.Afficher_rapport(rapport, "La fusion des individus a été effectuée. Le détail est consultable dans l'historique de la famille.")
        if familles_doublon - {self.kwargs["idfamille"]}:
            messages.add_message(request, messages.INFO, "L'individu est désormais rattaché à toutes les familles de la fiche absorbée.")
        return redirect("famille_resume", idfamille=self.kwargs["idfamille"])
