# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

""" Export et import de fiches familles entre deux bases Noethysweb (réservé aux super-utilisateurs) """

import datetime, json, logging
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.views.generic import TemplateView
from core.views.base import CustomView
from core.utils import utils_historique
from fiche_famille.utils import utils_transfert_familles as transfert

logger = logging.getLogger(__name__)

CLE_SESSION = "import_familles"


def Exporter(request):
    """ Génère et renvoie l'archive chiffrée des familles cochées (requête AJAX) """
    if request.method != "POST" or not request.user.is_superuser or not request.user.has_perm("core.famille_liste") or settings.MODE_DEMO:
        return HttpResponseForbidden()
    try:
        idfamilles = [int(idfamille) for idfamille in json.loads(request.POST.get("idfamilles", "[]"))]
    except (ValueError, TypeError):
        return JsonResponse({"erreur": "La sélection de familles n'est pas valide."}, status=400)
    mot_de_passe = request.POST.get("mot_de_passe", "")
    if mot_de_passe != request.POST.get("confirmation", ""):
        return JsonResponse({"erreur": "Le mot de passe et sa confirmation sont différents."}, status=400)
    try:
        contenu, stats = transfert.Exporter(idfamilles=idfamilles, mot_de_passe=mot_de_passe, utilisateur=request.user)
    except transfert.Erreur_transfert as err:
        return JsonResponse({"erreur": str(err)}, status=400)

    utils_historique.Ajouter(titre="Export de fiches familles", utilisateur=request.user,
                             detail="%d familles et %d individus exportés" % (stats["familles"], stats["individus"]))
    reponse = HttpResponse(contenu, content_type="application/x-7z-compressed")
    reponse["Content-Disposition"] = 'attachment; filename="export_familles_%s.7z"' % datetime.date.today().isoformat()
    return reponse


class Page(CustomView, TemplateView):
    menu_code = "famille_liste"
    template_name = "fiche_famille/familles_import.html"
    compatible_demo = False

    def test_func_page(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context["page_titre"] = "Gestion des familles"
        context["box_titre"] = "Importer des fiches familles"
        context["mdp_longueur_min"] = transfert.MDP_LONGUEUR_MIN
        return context

    def Get_session(self):
        donnees = self.request.session.get(CLE_SESSION)
        if not donnees:
            raise transfert.Erreur_transfert("Aucun import en cours. Veuillez sélectionner un fichier.")
        return donnees

    def Get_analyse(self):
        donnees = self.Get_session()
        archive = transfert.Archive(transfert.Get_chemin_temp(donnees["jeton"]), transfert.Dechiffrer_mdp(donnees["mot_de_passe"]))
        return transfert.Analyse(archive)

    def Erreur(self, err):
        messages.add_message(self.request, messages.ERROR, str(err))
        return redirect("familles_importer")


class Importer(Page):
    """ Étape 1 : envoi du fichier et du mot de passe """

    def get_context_data(self, **kwargs):
        context = super(Importer, self).get_context_data(**kwargs)
        context["etape"] = "envoi"
        context["box_introduction"] = "Sélectionnez un fichier d'export de fiches familles Noethysweb et saisissez son mot de passe."
        return context

    def post(self, request, *args, **kwargs):
        fichier = request.FILES.get("fichier")
        mot_de_passe = request.POST.get("mot_de_passe", "")
        if not fichier or not mot_de_passe:
            return self.Erreur("Veuillez sélectionner un fichier et saisir son mot de passe.")

        # Ancien import abandonné
        if request.session.get(CLE_SESSION):
            transfert.Supprimer_fichier_temp(request.session[CLE_SESSION].get("jeton"))

        request.session.pop(CLE_SESSION, None)
        try:
            jeton = transfert.Enregistrer_fichier_temp(fichier)
        except transfert.Erreur_transfert as err:
            return self.Erreur(err)
        try:
            transfert.Archive(transfert.Get_chemin_temp(jeton), mot_de_passe)
        except transfert.Erreur_transfert as err:
            transfert.Supprimer_fichier_temp(jeton)
            return self.Erreur(err)

        # Le mot de passe n'est conservé que chiffré, pour une heure au maximum
        request.session[CLE_SESSION] = {"jeton": jeton, "mot_de_passe": transfert.Chiffrer_mdp(mot_de_passe)}
        return redirect("familles_importer_analyse")


class Analyser(Page):
    """ Étape 2 : sélection des familles, doublons et correspondances des paramètres """

    def get(self, request, *args, **kwargs):
        try:
            self.analyse = self.Get_analyse()
        except transfert.Erreur_transfert as err:
            return self.Erreur(err)
        return super(Analyser, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(Analyser, self).get_context_data(**kwargs)
        context["etape"] = "analyse"
        context["box_introduction"] = "Cochez les familles à importer et vérifiez les doublons et les correspondances. Rien n'est enregistré avant la validation."
        context.update(self.analyse.Get_contexte())
        return context


class Executer(Page):
    """ Étape 3 : import et rapport """

    def get(self, request, *args, **kwargs):
        return redirect("familles_importer")

    def post(self, request, *args, **kwargs):
        try:
            analyse = self.Get_analyse()
        except transfert.Erreur_transfert as err:
            return self.Erreur(err)

        familles = request.POST.getlist("familles")
        if not familles:
            messages.add_message(request, messages.ERROR, "Veuillez cocher au moins une famille à importer.")
            return redirect("familles_importer_analyse")

        decisions_doublons = {idindividu: request.POST.get("doublon_%s" % idindividu, "ignorer") for idindividu in analyse.doublons}
        decisions_refs = {}
        for cle in analyse.references:
            valeur = request.POST.get("ref_%s" % cle.replace(":", "_"))
            if valeur:
                decisions_refs[cle] = valeur

        importation = transfert.Importation(analyse, familles=familles, decisions_doublons=decisions_doublons,
                                            decisions_refs=decisions_refs, utilisateur=request.user)
        try:
            rapport = importation.Executer()
        except Exception as err:
            logger.exception("Erreur pendant l'import de fiches familles")
            messages.add_message(request, messages.ERROR, "L'import a échoué et aucune donnée n'a été enregistrée. Détail : %s" % err)
            return redirect("familles_importer_analyse")

        # Historique
        origine = analyse.archive.manifeste.get("origine", "")
        utils_historique.Ajouter(titre="Import de fiches familles", utilisateur=request.user,
                                 detail="%d familles et %d individus importés depuis « %s »" % (rapport["familles"], rapport["individus"], origine))
        utils_historique.Ajouter_plusieurs([{"titre": "Import de la fiche famille", "detail": "Depuis « %s »" % origine,
                                             "utilisateur": request.user, "famille_id": idfamille} for idfamille in importation.map_familles.values()])

        # Nettoyage
        transfert.Supprimer_fichier_temp(request.session[CLE_SESSION]["jeton"])
        del request.session[CLE_SESSION]

        context = self.get_context_data(**kwargs)
        context["etape"] = "rapport"
        context["box_titre"] = "Import terminé"
        context["box_introduction"] = ""
        context["rapport"] = rapport
        context["manifeste"] = analyse.archive.manifeste
        return self.render_to_response(context)
