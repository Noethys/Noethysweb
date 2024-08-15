# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
logger = logging.getLogger(__name__)
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView
from django.template import Template, RequestContext
from django.db.models import Count, Q
from core.views.base import CustomView
from core.utils import utils_dates
from core.models import Consommation, Tarif, Unite, Activite, Prestation
from facturation.forms.saisie_lot_forfaits_credits import Formulaire
from consommations.utils.utils_grille_virtuelle import Grille_virtuelle


def Appliquer(request):
    # Récupération des variables
    selections = json.loads(request.POST.get("selections"))
    date_debut = utils_dates.ConvertDateENGtoDate(request.POST.get("date_debut"))
    date_fin = utils_dates.ConvertDateENGtoDate(request.POST.get("date_fin"))
    tarif = Tarif.objects.get(pk=request.POST.get("idtarif"))
    activite = Activite.objects.get(pk=request.POST.get("idactivite"))

    # Recherche de la date de facturation
    date_facturation = date_debut
    if tarif.date_facturation == "date_saisie": date_facturation = datetime.date.today()
    elif tarif.date_facturation == "date_debut_activite": date_facturation = activite.date_debut
    elif tarif.date_facturation and tarif.date_facturation.startswith("date:"): date_facturation = utils_dates.ConvertDateENGtoDate(tarif.date_facturation[5:])

    # Traitement
    logger.debug("Lancement application lot forfaits-crédits...")
    from consommations.views.grille import Facturation
    facturation = Facturation()
    for selection in selections:
        logger.debug("Application d'un forfait-crédit pour %s..." % selection["0"])

        # Calcul du tarif pour l'individu
        resultat = facturation.Calcule_tarif(tarif=tarif, case_tableau={"date": date_debut, "famille": selection["idfamille"]})
        if resultat:
            montant_tarif, nom_tarif, temps_facture, quantite, tarif_ligne = resultat

            # Enregistrement de la prestation du forfait-crédit
            prestation = Prestation(
                date=date_facturation,
                categorie="consommation",
                label=nom_tarif,
                montant_initial=montant_tarif,
                montant=montant_tarif,
                activite=activite,
                tarif=tarif,
                famille_id=selection["idfamille"],
                individu_id=selection["idindividu"],
                categorie_tarif_id=selection["idcategorie_tarif"],
                temps_facture=temps_facture,
                quantite=quantite or 1,
                tarif_ligne=tarif_ligne,
                tva=tarif.tva,
                code_compta=tarif.code_compta,
                forfait_date_debut=date_debut,
                forfait_date_fin=date_fin,
            )
            prestation.save()

            # Mise à jour des consommations
            grille = Grille_virtuelle(request=request, idfamille=selection["idfamille"], idindividu=selection["idindividu"], idactivite=activite.pk, date_min=date_debut, date_max=date_fin)
            grille.Recalculer_tout()
            grille.Enregistrer()

    logger.debug("Fin de la procédure application lot forfaits-crédits.")
    return JsonResponse({"resultat": True})


def Get_tarifs(request):
    """ Renvoie la liste des tarifs de type forfaits crédits pour une activité donnée """
    idactivite = request.POST.get("idactivite")
    periode = utils_dates.ConvertPeriodeFrToDate(request.POST.get("periode"))
    if not idactivite:
        resultat = ""
    else:
        conditions = (Q(date_fin__isnull=True) | Q(date_fin__gte=periode[0])) & Q(date_debut__lte=periode[0], activite_id=idactivite, type="CREDIT", forfait_beneficiaire="individu")
        tarifs = Tarif.objects.select_related("nom_tarif").filter(conditions)
        html = """
        <option value="">---------</option>
        {% for tarif in tarifs %}
            <option value="{{ tarif.pk }}">{{ tarif }}</option>
        {% endfor %}
        """
        context = {"tarifs": tarifs}
        resultat = Template(html).render(RequestContext(request, context))
    return HttpResponse(resultat)


class View(CustomView, TemplateView):
    menu_code = "saisie_lot_forfaits_credits"
    template_name = "facturation/saisie_lot_forfaits_credits.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = "Saisir un lot de forfaits-crédits"
        if "form_parametres" not in kwargs:
            context['form_parametres'] = Formulaire(request=self.request)
        return context

    def post(self, request, **kwargs):
        form = Formulaire(request.POST, request=self.request)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form_parametres=form))

        data = self.Get_resultats(parametres=form.cleaned_data)
        context = {"form_parametres": form, "data": data}
        return self.render_to_response(self.get_context_data(**context))

    def Get_resultats(self, parametres={}):
        date_debut, date_fin = utils_dates.ConvertDateRangePicker(parametres["periode"])
        activite = parametres["activite"]
        tarif = parametres["tarif"]

        individus = (Consommation.objects.select_related("inscription", "inscription__famille", "unite", "categorie_tarif")
                          .values("individu", "individu__nom", "individu__prenom", "unite", "inscription__famille", "inscription__famille__nom", "categorie_tarif", "categorie_tarif__nom")
                          .filter(date__gte=date_debut, date__lte=date_fin, activite=activite, categorie_tarif__in=tarif.categories_tarifs.all())
                          .annotate(nbre_consommations=Count("pk"))).order_by("individu__nom", "individu__prenom")

        resultats = {}
        for individu in individus:
            key = (individu["individu"], individu["inscription__famille"])
            resultats.setdefault(key, {"idindividu": individu["individu"], "nom": individu["individu__nom"], "prenom": individu["individu__prenom"],
                                       "idfamille": individu["inscription__famille"], "nom_famille": individu["inscription__famille__nom"],
                                       "idcategorie_tarif": individu["categorie_tarif"], "nom_categorie": individu["categorie_tarif__nom"],
                                       "unites": {}})
            resultats[key]["unites"][individu["unite"]] = individu["nbre_consommations"]

        # Création des colonnes
        unites = Unite.objects.filter(activite=activite).order_by("ordre")
        liste_colonnes = ["Individu", "Famille", "Catégorie"]
        dict_colonnes_unites = {unite.pk: index for index, unite in enumerate(unites, len(liste_colonnes))}
        liste_colonnes += [unite.nom for unite in unites]

        # Création des lignes
        liste_lignes = []
        for key, resultat in resultats.items():
            ligne = {
                "idindividu": resultat["idindividu"],
                "idfamille": resultat["idfamille"],
                "idcategorie_tarif": resultat["idcategorie_tarif"],
                "0": "%s %s" % (resultat["nom"], resultat["prenom"] or ""),
                "1": resultat["nom_famille"],
                "2": resultat["nom_categorie"],
            }
            for idunite in resultat["unites"]:
                ligne[str(dict_colonnes_unites[idunite])] = resultat["unites"].get(idunite, 0)
            liste_lignes.append(ligne)

        # Préparation des résultats
        data = {
            "date_debut": date_debut,
            "date_fin": date_fin,
            "liste_colonnes": liste_colonnes,
            "liste_lignes": json.dumps(liste_lignes),
            "activite": activite,
            "tarif": tarif,
        }
        return data
