# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
logger = logging.getLogger(__name__)
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.contrib import messages
from django.db.models import Q, Count
from crispy_forms.utils import render_crispy_form
from core.views import crud
from core.models import PortailRenseignement, Piece, TypePiece, Inscription
from portail.forms.inscrire_activite import Formulaire, Formulaire_extra
from portail.views.base import CustomView


def Get_form_extra(request):
    """ Retourne un form avec le groupe et les documents """
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        return JsonResponse({"form_html": None})

    # Création du contexte
    context = {}
    context.update(csrf(request))

    # Rendu du form en html
    form = Formulaire_extra(request=request, activite=form.cleaned_data["activite"], famille=form.cleaned_data["famille"], individu=form.cleaned_data["individu"])
    form_html = render_crispy_form(form, context=context)
    return JsonResponse({"form_html": form_html})


def Valid_form(request):
    """ Validation du form principal et du form extra """
    # Validation du formulaire principal
    form = Formulaire(request.POST, request=request)
    if not form.is_valid():
        messages_erreurs = ["%s : %s" % (field.title(), erreur[0].message) for field, erreur in form.errors.as_data().items()]
        return JsonResponse({"erreur": ", ".join(messages_erreurs)}, status=401)

    # Validation du formulaire extra (groupe et documents)
    form_extra = Formulaire_extra(request.POST, request.FILES, request=request, activite=form.cleaned_data["activite"], famille=form.cleaned_data["famille"], individu=form.cleaned_data["individu"])
    if not form_extra.is_valid():
        return JsonResponse({"erreur": "L'un des fichiers n'est pas valide. Vérifiez que le fichier est bien de type pdf, jpg ou png."}, status=401)

    # Récupération des données
    famille = form.cleaned_data["famille"]
    individu = form.cleaned_data["individu"]
    activite = form.cleaned_data["activite"]
    groupe = form_extra.cleaned_data["groupe"]
    categorie_tarif = form_extra.cleaned_data["categorie_tarif"]

    if not activite.inscriptions_multiples:

        # Vérifie que l'individu n'est pas déjà inscrit à cette activité
        if Inscription.objects.filter(famille=famille, individu=individu, activite=activite).exists():
            return JsonResponse({"erreur": "Cet individu est déjà inscrit à cette activité"}, status=401)

        # Vérifie qu'il n'y a pas déjà une demande en attente pour la même activité et le même individu
        for demande in PortailRenseignement.objects.filter(famille=famille, individu=individu, etat="ATTENTE", code="inscrire_activite"):
            if int(json.loads(demande.nouvelle_valeur).split(";")[0]) == activite.pk:
                return JsonResponse({"erreur": "Une demande en attente de traitement existe déjà pour cet individu et cette activité"}, status=401)

    # Vérifie s'il reste de la place
    if activite.portail_inscriptions_bloquer_si_complet:
        places_prises = Inscription.objects.filter(activite=activite).aggregate(
            total=Count("pk", filter=Q(statut="ok")), attente=Count("pk", filter=Q(statut="attente")),
            total_groupe=Count("pk", filter=Q(statut="ok", groupe=groupe)), attente_groupe=Count("pk", filter=Q(statut="attente", groupe=groupe)),
        )
        if activite.nbre_inscrits_max and places_prises["total"] >= activite.nbre_inscrits_max:
            return JsonResponse({"erreur": "Cette activité est déjà complète"}, status=401)
        if groupe.nbre_inscrits_max and places_prises["total_groupe"] >= groupe.nbre_inscrits_max:
            return JsonResponse({"erreur": "Ce groupe est déjà complet"}, status=401)

    # Enregistrement de la demande
    demande = form.save()
    demande.nouvelle_valeur = json.dumps("%d;%d;%d" % (activite.pk, groupe.pk, categorie_tarif.pk ), cls=DjangoJSONEncoder)
    demande.save()

    # Enregistrement des pièces
    for nom_champ, valeur in form_extra.cleaned_data.items():
        if nom_champ.startswith("document_"):
            type_piece = TypePiece.objects.get(pk=int(nom_champ.split("_")[1]))

            # Paramètres de la pièce à enregistrer
            individu = None if type_piece.public == "famille" else form.cleaned_data["individu"]
            famille = None if type_piece.public == "individu" and type_piece.valide_rattachement else form.cleaned_data["famille"]

            # Enregistrement de la pièce
            piece = Piece.objects.create(type_piece=type_piece, famille=famille, individu=individu, auteur=request.user, document=valeur,
                                         date_debut=datetime.date.today(), date_fin=type_piece.Get_date_fin_validite())

            # Enregistrement du renseignement de portail
            PortailRenseignement.objects.create(famille=famille, individu=individu, categorie="famille_pieces", code="Nouvelle pièce", validation_auto=True,
                                                nouvelle_valeur=json.dumps(piece.Get_nom(), cls=DjangoJSONEncoder), idobjet=piece.pk)

    # Message de confirmation
    messages.add_message(request, messages.SUCCESS, "Votre demande d'inscription a été transmise")

    # Retour de la réponse
    return JsonResponse({"succes": True, "url": reverse_lazy("portail_activites")})


class Page(CustomView):
    model = PortailRenseignement
    menu_code = "portail_activites"

    def get_context_data(self, **kwargs):
        context = super(Page, self).get_context_data(**kwargs)
        context['page_titre'] = _("Inscrire à une nouvelle activité")
        context['box_titre'] = None
        context['box_introduction'] = _("Renseignez les paramètres ci-dessous et cliquez sur le bouton Envoyer la demande d'inscription.")
        return context

    def get_success_url(self):
        return reverse_lazy("portail_activites")


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    texte_confirmation = _("La demande a bien été transmise")
    titre_historique = "Inscrire à une activité"
    template_name = "portail/edit.html"

    def Get_detail_historique(self, instance):
        return "Famille=%s, Individu=%s" % (instance.famille, instance.individu)
