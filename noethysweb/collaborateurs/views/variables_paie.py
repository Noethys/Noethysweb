# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.http import JsonResponse
from django.views.generic import TemplateView
from django.db.models import Q, Exists, OuterRef
from core.views.base import CustomView
from core.models import ContratCollaborateur
from collaborateurs.forms.planning_absences import Lire_mois, NOMS_MOIS
from collaborateurs.forms.variables_paie import Formulaire
from collaborateurs.utils import utils_paie
from collaborateurs.views.planning_individuel import Collaborateurs_accessibles

PERMISSION = "core.variables_paie_collaborateurs"


def Format_heures(minutes=None):
    if minutes is None:
        return ""
    if abs(minutes) < 0.5:
        return ""
    signe = "-" if minutes < 0 else ""
    minutes = int(round(abs(minutes)))
    return "%s%dh%02d" % (signe, minutes // 60, minutes % 60)


def Format_nombre(valeur=0):
    return ("%.2f" % valeur).rstrip("0").rstrip(".").replace(".", ",") if valeur else ""


def Get_resultats(parametres={}, user=None):
    mois = Lire_mois(parametres["mois"])
    date_debut, date_fin = utils_paie.Limites_mois(mois)
    collaborateurs = Collaborateurs_accessibles(user).filter(Exists(ContratCollaborateur.objects.filter(
        Q(date_debut__lte=date_fin) & (Q(date_fin__isnull=True) | Q(date_fin__gte=date_debut)), collaborateur=OuterRef("pk"))))
    if parametres.get("groupes"):
        collaborateurs = collaborateurs.filter(groupes__in=parametres["groupes"])
    return utils_paie.Calculer(mois=mois, collaborateurs=collaborateurs.distinct().order_by("nom", "prenom"), realise=parametres["donnees"] == "REALISE",
                               duree_legale=float(parametres["duree_legale"]), rattachement=parametres["rattachement"])


def Mettre_en_forme(resultats={}):
    """ Textes affichés dans le tableau de la page """
    for ligne in resultats["lignes"]:
        ligne["textes"] = {cle: Format_heures(ligne[cle]) for cle in ("travaille", "assimile", "attendu", "ecart", "hc10", "hc25", "hs25", "hs50", "dimanche", "ferie", "nuit")}
        ligne["textes_conges"] = []
        for colonne in resultats["colonnes_conges"]:
            valeur = ligne["conges"][colonne["index"]]
            ligne["textes_conges"].append(Format_heures(valeur * 60) if colonne["unite"] == "HEURES" else (Format_nombre(valeur) + " j" if valeur else ""))
        ligne["textes_absences"] = []
        for colonne in resultats["colonnes_absences"]:
            absence = ligne["absences"][colonne["index"]]
            ligne["textes_absences"].append("%s j" % Format_nombre(absence["jours"]) if absence["jours"] else "")
    totaux = {}
    for cle in ("travaille", "hc10", "hc25", "hs25", "hs50", "dimanche", "ferie", "nuit"):
        totaux[cle] = Format_heures(sum(ligne[cle] for ligne in resultats["lignes"]))
    resultats["totaux"] = totaux
    resultats["titre_mois"] = "%s %d" % (NOMS_MOIS[resultats["date_debut"].month - 1], resultats["date_debut"].year)
    resultats["nbre_colonnes_absences"] = len(resultats["colonnes_conges"]) + len(resultats["colonnes_absences"])
    resultats["nbre_alertes"] = len([ligne for ligne in resultats["lignes"] if ligne["alertes"]])
    resultats["semaines_textes"] = ["%s au %s" % (lundi.strftime("%d/%m"), dimanche.strftime("%d/%m")) for lundi, dimanche in resultats["semaines"]]
    return resultats


def Exporter_excel(request):
    if not request.user.has_perm(PERMISSION):
        return JsonResponse({"erreur": "Vous n'avez pas l'autorisation d'accéder à cette fonctionnalité"}, status=403)
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"erreur": "Les paramètres sont incorrects"}, status=400)
    resultats = Get_resultats(form.cleaned_data, request.user)
    if not resultats["lignes"]:
        return JsonResponse({"erreur": "Aucun collaborateur sous contrat sur ce mois"}, status=400)
    return JsonResponse({"url": utils_paie.Exporter_excel(resultats, format_heures=form.cleaned_data["format_heures"])})


class View(CustomView, TemplateView):
    menu_code = "variables_paie_collaborateurs"
    template_name = "collaborateurs/variables_paie.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Éléments variables de paie"
        if "form_parametres" not in kwargs:
            context["form_parametres"] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))
        return self.render_to_response(self.get_context_data(form_parametres=form, resultats=Mettre_en_forme(Get_resultats(form.cleaned_data, request.user))))
