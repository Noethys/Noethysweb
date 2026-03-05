# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import logging, json, datetime
logger = logging.getLogger(__name__)
from django import forms
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.template.context_processors import csrf
from django.contrib import messages
from django.db.models import Q, Count
from crispy_forms.utils import render_crispy_form
from core.views import crud
from core.models import PortailRenseignement, Piece, TypePiece, Inscription, Individu, Rattachement, NomTarif, Tarif, Activite, Groupe, Structure
from portail.forms.inscrire_activite import Formulaire, Formulaire_extra
from portail.views.base import CustomView
from django.forms import formset_factory


def Get_activites_par_structure(request):
    structure_id = request.POST.get('structure_id')
    # On filtre et on s'assure d'avoir des objets valides
    activites = Activite.objects.filter(structure_id=structure_id, visible=True).order_by('nom')

    activites_data = []
    for a in activites:
        # On récupère les groupes liés à l'activité
        # Attention : vérifie si dans ton modèle c'est 'id' ou 'idgroupe'
        groupes = list(Groupe.objects.filter(activite=a).values('idgroupe', 'nom'))

        activites_data.append({
            'id': a.pk,
            'nom': a.nom,
            'groupes': groupes
        })
    return JsonResponse({'activites': activites_data})


def Get_form_extra(request):
    """ Retourne le formulaire dynamique (Groupe + Tarifs + Pièces) """
    # On récupère les IDs envoyés par le script JS
    individu_id = request.POST.get('individu')
    activite_id = request.POST.get('activite')

    # Sécurité : on vérifie que les deux sont présents
    if not individu_id or not activite_id:
        return JsonResponse({
            "form_html": "<div class='alert alert-info small'><i class='fa fa-info-circle mr-2'></i> "
                         "Veuillez sélectionner un individu et une activité.</div>"
        })

    try:
        # On récupère les objets en base
        activite = Activite.objects.get(pk=activite_id)
        individu = Individu.objects.get(pk=individu_id)
        famille = request.user.famille  # On utilise la famille de la session

        # On prépare le formulaire extra avec ces objets
        form = Formulaire_extra(
            activite=activite,
            famille=famille,
            individu=individu
        )

        form_html = render_crispy_form(form, context=csrf(request))
        return JsonResponse({"form_html": form_html})

    except (Activite.DoesNotExist, Individu.DoesNotExist):
        return JsonResponse({"form_html": "<div class='alert alert-danger'>Erreur : Données introuvables.</div>"})


def Valid_form(request):
    print("--- Début de la validation ---")

    # 1. On prépare les données (Copie pour injecter les champs Hidden manquants)
    data = request.POST.copy()
    if not data.get('famille'): data['famille'] = request.user.famille.pk
    if not data.get('etat'): data['etat'] = 'ATTENTE'
    if not data.get('categorie'): data['categorie'] = 'activites'
    if not data.get('code'): data['code'] = 'inscrire_activite'

    # 2. Validation du formulaire principal
    form = Formulaire(data, request=request)

    # On élargit les querysets pour que Django accepte les IDs envoyés par AJAX
    form.fields["activite"].queryset = Activite.objects.all()
    form.fields["groupe"].queryset = Groupe.objects.all()
    form.fields["structure"].queryset = Structure.objects.all()

    if not form.is_valid():
        print(f"DEBUG ERRORS PRINCIPAL: {form.errors.as_json()}")
        return JsonResponse({"erreur": f"Formulaire principal invalide : {form.errors}"}, status=400)

    print("--- Formulaire principal VALIDE ! ---")

    # 3. Validation du formulaire EXTRA (Tarifs et Pièces)
    form_extra = Formulaire_extra(
        request.POST,
        request.FILES,
        activite=form.cleaned_data["activite"],
        famille=form.cleaned_data["famille"],
        individu=form.cleaned_data["individu"]
    )

    if not form_extra.is_valid():
        print(f"DEBUG ERRORS EXTRA: {form_extra.errors.as_json()}")
        first_error = list(form_extra.errors.values())[0][0]
        return JsonResponse({"erreur": f"Erreur détails : {first_error}"}, status=400)

    # 4. Récupération des données validées
    famille = form.cleaned_data["famille"]
    individu = form.cleaned_data["individu"]
    activite = form.cleaned_data["activite"]

    # ATTENTION : Le groupe est maintenant dans 'form', plus dans 'form_extra'
    groupe = form.cleaned_data["groupe"]

    # 5. Gestion des tarifs
    liste_nom_tarif = NomTarif.objects.filter(activite=activite).order_by("nom").distinct()
    id_tarifs_selectionnes = []
    for nom_tarif in liste_nom_tarif:
        field_name = f"tarifs_{nom_tarif.idnom_tarif}"
        tarifs_selectionnes = request.POST.getlist(field_name)
        id_tarifs_selectionnes.extend(tarifs_selectionnes)

    if not id_tarifs_selectionnes:
        return JsonResponse({"erreur": "Vous devez sélectionner au moins un tarif"}, status=401)

        # Vérifie qu'il n'y a pas déjà une demande en attente pour la même activité et le même individu
        for demande in PortailRenseignement.objects.filter(famille=famille, individu=individu, etat="ATTENTE",
                                                           code="inscrire_activite"):
            try:
                activite_id = json.loads(demande.nouvelle_valeur).split(";")[0]
                if int(activite_id) == activite.pk:
                    return JsonResponse({
                        "erreur": "Une demande en attente de traitement existe déjà pour cet individu et cette activité"},
                        status=401)
            except (json.JSONDecodeError, ValueError) as e:
                # Gérer les erreurs de décodage JSON ou conversion en entier
                print(f"Erreur lors de la vérification de la demande en attente : {e}")
                # Continuer le traitement des autres demandes

    # Vérifie s'il reste de la place
    if activite.portail_inscriptions_bloquer_si_complet:
        places_prises = Inscription.objects.filter(activite=activite).aggregate(
            total=Count("pk", filter=Q(statut="ok")), attente=Count("pk", filter=Q(statut="attente")),
            total_groupe=Count("pk", filter=Q(statut="ok", groupe=groupe)),
            attente_groupe=Count("pk", filter=Q(statut="attente", groupe=groupe)),
        )
        if activite.nbre_inscrits_max and places_prises["total"] >= activite.nbre_inscrits_max:
            return JsonResponse({"erreur": "Cette activité est déjà complète"}, status=401)
        if groupe.nbre_inscrits_max and places_prises["total_groupe"] >= groupe.nbre_inscrits_max:
            return JsonResponse({"erreur": "Ce groupe est déjà complet"}, status=401)

    inscription_famille = Inscription.objects.filter(activite=activite, famille=famille)

    if activite.maitrise and individu.statut in [0]:
        return JsonResponse({
                                "erreur": "Cet individu ne peut pas s'inscrire à cette activité. Si vous êtes responsable dans cette activité, veuillez changer votre statut dans votre fiche (onglet identité)."},
                            status=401)

    if activite.public in [0, 1, 2, 3, 4, 6] and individu.statut not in [0, 1, 2, 3, 4] and not inscription_famille:
        return JsonResponse({
                                "erreur": "Cet individu ne peut pas s'inscrire à cette activité. Un adulte responsable doit être inscrit au préalable."},
                            status=401)

    # 7. Enregistrement de la demande
    try:
        demande = form.save(commit=False)
        demande.validation_auto = False
        # On construit la valeur Noethys : ID_ACT;ID_GROUPE;JSON_TARIFS
        demande.nouvelle_valeur = json.dumps("%d;%d;%s" % (activite.pk, groupe.pk, json.dumps(id_tarifs_selectionnes)),
                                             cls=DjangoJSONEncoder)
        demande.activite = activite
        demande.save()
        print(f"Demande enregistrée ! ID: {demande.pk}")
    except Exception as e:
        print(f"Erreur enregistrement : {e}")
        return JsonResponse({"erreur": "Erreur lors de la sauvegarde de la demande"}, status=500)

    # 8. Enregistrement des pièces jointes uploadées
    for nom_champ, valeur in form_extra.cleaned_data.items():
        if nom_champ.startswith("document_") and valeur:
            try:
                # Extraction de l'ID du type de pièce depuis le nom du champ (document_XXX)
                type_piece = TypePiece.objects.get(pk=int(nom_champ.split("_")[1]))

                # Paramètres de la pièce à enregistrer selon le type
                if type_piece.public == "individu":
                    piece_individu = form.cleaned_data["individu"]
                    # Si valide_rattachement, on ne met PAS la famille (la pièce est liée uniquement à l'individu)
                    piece_famille = None if type_piece.valide_rattachement else form.cleaned_data["famille"]
                else:  # famille
                    piece_individu = None
                    piece_famille = form.cleaned_data["famille"]
                                
                # Création de la pièce
                piece = Piece.objects.create(
                    titre=type_piece.nom,
                    document=valeur,
                    famille=piece_famille,
                    individu=piece_individu,
                    type_piece=type_piece,
                    date_debut=datetime.date.today(),
                    date_fin=type_piece.Get_date_fin_validite(),
                    auteur=request.user
                )
                
                # Enregistrement du renseignement de portail (utiliser la famille du form, pas la variable locale)
                PortailRenseignement.objects.create(
                    famille=form.cleaned_data["famille"], 
                    individu=form.cleaned_data["individu"], 
                    categorie="famille_pieces", 
                    code="Nouvelle pièce", 
                    validation_auto=True,
                    nouvelle_valeur=json.dumps(piece.Get_nom(), cls=DjangoJSONEncoder), 
                    idobjet=piece.pk
                )
                
                logger.info(f"Pièce '{type_piece.nom}' uploadée pour {piece_individu or 'la famille'} lors de l'inscription à {activite}")
            
            except (ValueError, TypePiece.DoesNotExist) as e:
                logger.error(f"Erreur lors de l'enregistrement de la pièce {nom_champ}: {e}")
                # On continue malgré l'erreur pour ne pas bloquer l'inscription
            except Exception as e:
                logger.error(f"Erreur inattendue lors de l'enregistrement de la pièce {nom_champ}: {e}")
                # On continue malgré l'erreur pour ne pas bloquer l'inscription

    messages.add_message(request, messages.SUCCESS, "Votre demande d'inscription a été transmise")
    return JsonResponse({"succes": True, "url": reverse_lazy("portail_activites")})


class Page(CustomView):
    model = PortailRenseignement
    menu_code = "portail_activites"
    template_name = "portail/inscription_activite_custom.html"
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
    template_name = "portail/inscription_activite_custom.html"

    def Get_detail_historique(self, instance):
        return "Famille=%s, Individu=%s" % (instance.famille, instance.individu)
