# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
logger = logging.getLogger(__name__)
from django.views.generic import TemplateView
from django.db.models import Q, Count, Min, Max
from django.urls import reverse
from django.http import JsonResponse
from django.template import Template, RequestContext
from core.views.base import CustomView
from core.models import Consommation, Inscription, Unite, Mail, Destinataire
from core.utils import utils_dates
from outils.utils import utils_email
from consommations.views import suivi_consommations
from consommations.utils.utils_grille_virtuelle import Grille_virtuelle


def Get_detail_demande(request):
    demande = json.loads(request.POST["demande"])
    index = request.POST["index"]

    # Importation des données
    inscription = Inscription.objects.select_related("famille", "individu", "activite").get(pk=demande["inscription"])
    dict_dependances = {unite: unite.dependances.all() for unite in Unite.objects.filter(activite_id=inscription.activite_id, dependances__isnull=False)}
    consommations = Consommation.objects.select_related("unite", "evenement").filter(etat="demande", inscription=demande["inscription"], date_saisie=demande["date_saisie"]).order_by("date", "unite__ordre")
    envoi_notification_possible = True if inscription.activite.validation_modele_email and inscription.activite.reattribution_adresse_exp else False

    # Récupération du remplissage
    data_remplissage = suivi_consommations.Get_data(request=request, parametres={
        "condition_periodes": Q(date__gte=demande["date_min"]) & Q(date__lte=demande["date_max"]),
        "liste_activites": [inscription.activite]})

    liste_places_completes = []
    for conso in consommations:
        conso.code = "%s;%d;%d;%d" % (conso.date, conso.pk, conso.unite_id, conso.evenement_id or 0)

        # Etat des places
        place_dispo = True
        nbre_places_restantes = None

        if conso.evenement and conso.evenement.capacite_max:
            nbre_places_restantes = data_remplissage["dict_all_evenements"][conso.evenement_id].restantes if conso.evenement_id in data_remplissage["dict_all_evenements"] else 0
            if nbre_places_restantes <= 0:
                place_dispo = False
        else:
            if conso.unite_id in data_remplissage["dict_unites_remplissage_unites"]:
                for IDuniteRemplissage in data_remplissage["dict_unites_remplissage_unites"][conso.unite_id]:

                    # Récupère les places restantes du suivi des conso
                    key_unite_remplissage = "%s_%s_%s" % (conso.date, IDuniteRemplissage, conso.groupe.pk)
                    dict_places_unite_remplissage = data_remplissage["dict_cases"].get(key_unite_remplissage, None)

                    if dict_places_unite_remplissage and dict_places_unite_remplissage["initiales"] > 0:
                        nbre_places_restantes = None
                        if conso.evenement:
                            for evenement_tmp in dict_places_unite_remplissage["evenements"]:
                                if evenement_tmp.pk == conso.evenement.pk:
                                    nbre_places_restantes = evenement_tmp.restantes
                        else:
                            nbre_places_restantes = dict_places_unite_remplissage["restantes"]
                        if nbre_places_restantes <= 0:
                            place_dispo = False

        # Mémorise l'état des places dans l'instance de la consommation
        conso.place_dispo = place_dispo
        conso.nbre_places_restantes = nbre_places_restantes

        # Mémorisation des places complètes pour les dépendances d'unités
        if not place_dispo:
            liste_places_completes.append("%s_%d" % (conso.date, conso.unite_id))

    # Vérifie les dépendances d'unités
    if liste_places_completes and dict_dependances:
        for conso in consommations:
            for unite in dict_dependances.get(conso.unite, []):
                if "%s_%d" % (conso.date, unite.pk) in liste_places_completes:
                    conso.place_dispo = False

    html = """
    <style>
        .liste-consommations th {
            padding: 2px;
        }
        .liste-consommations .btn {
            background-color: #ededed;
        }
        .liste-consommations .reservation.active {
            background-color: #FF9E1E;
        }
        .liste-consommations .attente.active {
            background-color: #abcbff;
        }
        .liste-consommations .refus.active {
            background-color: #ff1904;
        }
    </style>
    <p>{{ demande.horodatage }} | <a href="{% url 'famille_resume' idfamille=inscription.famille_id %}" target="_blank" title="Ouvrir la fiche famille dans un nouvel onglet">{{ inscription.famille.nom }}</a> | {{ inscription.activite.nom }} | {{ inscription.individu.prenom }}</p>
    <input type="hidden" name="idinscription" value="{{ inscription.pk }}">
    <input type="hidden" name="date_saisie" value="{{ demande.date_saisie }}">
    <input type="hidden" name="index" value="{{ index }}">
    <table class="table text-center table-valign-middle liste-consommations mb-0" style="border: 1px solid #dee2e6">
        <tr><th>Date</th><th>Unité</th><th>Places</th><th>Décision</th></tr>
        {% for conso in consommations %}
            <tr>
                <td>{{ conso.date|date:"l j F Y"|capfirst }}</td>
                <td>{% if conso.evenement %}{{ conso.evenement.nom }}{% else %}{{ conso.unite.nom }}{% endif %}</td>
                <td>
                    {% if conso.place_dispo %}<span class="badge bg-success" title="Places restantes : {{ conso.nbre_places_restantes|default:'-' }}">Disponible</span>{% endif %}
                    {% if not conso.place_dispo %}<span class="badge bg-danger">Complet</span>{% endif %}
                </td>
                <td>
                    <div class="btn-group btn-group-toggle" data-toggle="buttons">
                        <label class="btn reservation {% if conso.place_dispo %}active{% endif %}" title="Accepter">
                            <input type="radio" name="{{ conso.code }}" data-decision="reservation" autocomplete="off" {% if conso.place_dispo %}checked{% endif %}><i class="fa fa-check"></i>
                        </label>
                        <label class="btn attente {% if not conso.place_dispo %}active{% endif %}" title="Mettre en attente">
                            <input type="radio" name="{{ conso.code }}" data-decision="attente" autocomplete="off" {% if not conso.place_dispo %}checked{% endif %}><i class="fa fa-hourglass-2"></i>
                        </label>
                        <label class="btn refus" title="Refuser">
                            <input type="radio" name="{{ conso.code }}" data-decision="refus" autocomplete="off"><i class="fa fa-remove"></i>
                        </label>
                    </div>
                </td>
            </tr>
        {% endfor %}
    </table>
    """
    context = {"consommations": consommations, "inscription": inscription, "demande": demande, "index": index}
    html_ctrl = Template(html).render(RequestContext(request, context))
    return JsonResponse({"html": html_ctrl, "envoi_notification_possible": envoi_notification_possible})


def Valider_demande(request):
    # Variables à récupérer
    idinscription = int(request.POST["idinscription"])
    index = int(request.POST["index"])
    dict_decisions = json.loads(request.POST["dict_decisions"])
    date_saisie = request.POST["date_saisie"]
    notification_active = request.POST["notification_active"]

    # Importation des données
    inscription = Inscription.objects.select_related("famille", "individu", "activite").get(pk=idinscription)

    consommations = Consommation.objects.select_related("unite", "evenement").filter(inscription=inscription, date_saisie=date_saisie).order_by("date", "unite__ordre")
    liste_dates = [key.split(";")[0] for key in dict_decisions.keys()]

    # Enregistrement des nouveaux états des consommations dans la grille virtuelle
    grille = Grille_virtuelle(request=request, idfamille=inscription.famille_id, idindividu=inscription.individu_id, idactivite=inscription.activite_id, date_min=min(liste_dates), date_max=max(liste_dates))
    for key, nouvel_etat in dict_decisions.items():
        date, idconso, idunite, idevenement = key.split(";")
        grille.Modifier(criteres={"idconso": idconso}, modifications={"etat": nouvel_etat})
    grille.Enregistrer()

    # Envoi du mail de confirmation à la famille
    if notification_active == "true" and inscription.activite.validation_modele_email and inscription.activite.reattribution_adresse_exp:

        # Préparation du mail à envoyer
        mail = Mail.objects.create(
            categorie="portail_demande_reservation",
            objet=inscription.activite.validation_modele_email.objet if inscription.activite.validation_modele_email else "",
            html=inscription.activite.validation_modele_email.html if inscription.activite.validation_modele_email else "",
            adresse_exp=inscription.activite.reattribution_adresse_exp,
            selection="NON_ENVOYE",
            utilisateur=request.user if request else None,
        )

        # Préparation du texte de l'email
        dict_etats = {"reservation": "Réservé", "attente": "Sur liste d'attente", "refus": "Refusé"}
        texte_detail = ""
        for conso in consommations:
            key = "%s;%d;%d;%d" % (conso.date, conso.pk, conso.unite_id, conso.evenement_id or 0)
            if key in dict_decisions:
                texte_detail += "- %s - %s : <b>%s</b><br>" % (utils_dates.DateComplete(conso.date), conso.evenement.nom if conso.evenement else conso.unite.nom, dict_etats[dict_decisions[key]])

        date_saisie_fr = datetime.datetime.strptime(date_saisie[:16], "%Y-%m-%d %H:%M")
        valeurs_fusion = {
            "{DEMANDE_REPONSE}": texte_detail, "{DEMANDE_HORODATAGE}": date_saisie_fr.strftime("%d/%m/%Y %H:%m"),
            "{INDIVIDU_NOM}": inscription.individu.nom, "{INDIVIDU_PRENOM}": inscription.individu.prenom, "{INDIVIDU_NOM_COMPLET}": inscription.individu.Get_nom()
        }
        destinataire = Destinataire.objects.create(categorie="famille", famille=inscription.famille, adresse=inscription.famille.mail, valeurs=json.dumps(valeurs_fusion))
        mail.destinataires.add(destinataire)

        # Envoi du mail
        utils_email.Envoyer_model_mail(idmail=mail.pk, request=request)

    return JsonResponse({"succes": True, "index": index})


class View(CustomView, TemplateView):
    menu_code = "liste_demandes"
    template_name = "consommations/liste_demandes.html"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context["page_titre"] = "Liste des demandes de réservations"
        context["resultats"] = self.Get_resultats()
        return context

    def Get_resultats(self):
        liste_lignes = []

        conditions = Q(etat="demande", activite__structure__in=self.request.user.structures.all())
        demandes = Consommation.objects.select_related("activite", "individu", "inscription", "inscription__famille", "inscription__groupe", "inscription__categorie_tarif") \
                         .values("date_saisie", "activite__nom", "individu__nom", "individu__prenom", "inscription", "inscription__famille_id", "inscription__famille__nom", "inscription__groupe__nom", "inscription__categorie_tarif__nom") \
                        .filter(conditions) \
                        .annotate(nbre_conso=Count("idconso"), date_min=Min("date"), date_max=Max("date")) \
                        .order_by("date_saisie")

        for index, demande in enumerate(demandes):
            liste_lignes.append({
                "date_saisie": str(demande["date_saisie"]),
                "inscription": demande["inscription"],
                "date_min": str(demande["date_min"]),
                "date_max": str(demande["date_max"]),
                "horodatage": demande["date_saisie"].strftime("%d/%m/%Y %H:%M"),
                "activite": demande["activite__nom"],
                "famille": demande["inscription__famille__nom"],
                "individu": "%s %s" % (demande["individu__nom"] or "", demande["individu__prenom"]),
                "groupe": demande["inscription__groupe__nom"],
                "categorie_tarif": demande["inscription__categorie_tarif__nom"],
                "nbre_conso": demande["nbre_conso"],
                "periode": "Du %s au %s" % (demande["date_min"].strftime("%d/%m/%Y"), demande["date_max"].strftime("%d/%m/%Y")),
                "action": """
                    <div class="m-2">
                        <button title='Consulter la demande' class='btn btn-default btn-xs' onclick='ouvre_modal_demande(%d)'><i class='fa fa-fw fa-search'></i></button>
                        <a type="button" class="btn btn-default btn-xs" href="%s" target="_blank" title="Ouvrir la fiche famille dans un nouvel onglet"><i class="fa fa-users"></i></a>
                    </div>""" % (index, reverse("famille_resume", args=[demande["inscription__famille_id"]])),
            })

        return {"liste_lignes": json.dumps(liste_lignes)}
