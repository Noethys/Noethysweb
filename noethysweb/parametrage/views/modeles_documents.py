# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import ModeleDocument, CHOIX_CATEGORIE_MODELE_DOCUMENT
from parametrage.forms.modeles_documents import Formulaire, Formulaire_creation, Formulaire_champs
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from reportlab.pdfgen.canvas import Canvas as CanvasPDF
from django.conf import settings
from core.utils import utils_modeles_documents, utils_fichiers
import json
from uuid import uuid4
from django.db.models import Q
from copy import deepcopy



def Export_svg(request, *args, **kwargs):
    objets_json = json.loads(request.POST.get("objets_json"))
    id_fond = request.POST.get("id_fond")
    largeur = request.POST.get("largeur")
    hauteur = request.POST.get("hauteur")
    nom = request.POST.get("nom")

    if not largeur or not hauteur:
        return JsonResponse({"erreur": "Veuillez saisir une largeur et une hauteur valide pour ce modèle."}, status=401)

    # Créé le répertoire temp s'il n'existe pas
    rep_temp = utils_fichiers.GetTempRep()

    # Initialisation du fichier
    nom_fichier = "/temp/%s.pdf" % uuid4()
    chemin_fichier = settings.MEDIA_ROOT + nom_fichier
    canvas = CanvasPDF(chemin_fichier, pagesize=utils_modeles_documents.ConvertTailleModeleEnPx((float(largeur), float(hauteur))))
    canvas.setTitle(nom)

    # Importation des objets du fond
    if id_fond:
        fond = ModeleDocument.objects.get(pk=id_fond)
        for objet in json.loads(fond.objets):
            utils_modeles_documents.ObjetPDF(objet, canvas, valeur=None)

    # Importation des objets du modèle
    for objet in objets_json:
        utils_modeles_documents.ObjetPDF(objet, canvas, valeur=None)

    # Finalisation du PDF
    canvas.showPage()
    canvas.save()
    return JsonResponse({"nom_fichier": nom_fichier})



def Get_fond_modele(request):
    id_fond = request.POST.get('id_fond')
    if id_fond:
        modele = ModeleDocument.objects.get(pk=id_fond)
        objets = modele.objets
    else:
        objets = []
    dict_resultats = {"objets": objets}
    return JsonResponse(dict_resultats)


class Page(crud.Page):
    model = ModeleDocument
    url_liste = "modeles_documents_liste"
    url_ajouter = "modeles_documents_creer"
    url_modifier = "modeles_documents_modifier"
    url_supprimer = "modeles_documents_supprimer"
    url_dupliquer = "modeles_documents_dupliquer"
    description_liste = "Voici ci-dessous la liste des modèles de documents pour chaque catégorie de données."
    description_saisie = "Saisissez toutes les informations concernant le modèle de document à saisir et cliquez sur le bouton Enregistrer."
    objet_singulier = "un modèle de document"
    objet_pluriel = "des modèles de documents"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['categorie'] = self.Get_categorie()
        context['label_categorie'] = "Catégorie"
        context['liste_categories'] = CHOIX_CATEGORIE_MODELE_DOCUMENT
        context['boutons_liste'] = [
            {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(self.url_ajouter, kwargs={'categorie': self.Get_categorie()}), "icone": "fa fa-plus"},
        ]
        return context

    def Get_categorie(self):
        return self.kwargs.get('categorie', 'facture')

    def get_form_kwargs(self, **kwargs):
        """ Envoie des kwargs au formulaire """
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["nom"] = self.kwargs.get("nom", None)
        form_kwargs["categorie"] = self.Get_categorie()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        return reverse_lazy(self.url_liste, kwargs={'categorie': self.Get_categorie()})


class Liste(Page, crud.Liste):
    model = ModeleDocument
    template_name = "core/crud/liste_avec_categorie.html"

    def get_queryset(self):
        return ModeleDocument.objects.filter(Q(categorie=self.Get_categorie()) & self.Get_filtres("Q"), self.Get_condition_structure())

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idmodele", "nom", 'defaut']

        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        categorie = columns.TextColumn("Catégorie", sources="categorie", processor='Get_categorie')
        dimensions = columns.TextColumn("Dimensions", sources=None, processor='Get_dimensions')
        defaut = columns.TextColumn("Défaut", sources="defaut", processor='Get_default')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idmodele", "nom", "categorie", "dimensions", 'defaut']
            ordering = ["nom"]

        def Get_categorie(self, instance, **kwargs):
            return instance.get_categorie_display()

        def Get_dimensions(self, instance, **kwargs):
            return "%d x %d mm" % (instance.largeur, instance.hauteur)

        def Get_actions_speciales(self, instance, *args, **kwargs):
            """ Inclut la catégorie dans les boutons d'actions """
            html = [
                self.Create_bouton_modifier(url=reverse(kwargs["view"].url_modifier, args=[instance.categorie, instance.pk])),
                self.Create_bouton_supprimer(url=reverse(kwargs["view"].url_supprimer, args=[instance.categorie, instance.pk])),
                self.Create_bouton_dupliquer(url=reverse(kwargs["view"].url_dupliquer, args=[instance.categorie, instance.pk])),
            ]
            return self.Create_boutons_actions(html)

        def Get_default(self, instance, **kwargs):
            return "<i class='fa fa-check text-success'></i>" if instance.defaut else ""


class Classe_commune(Page):
    form_class = Formulaire
    template_name = "parametrage/modeles_documents.html"

    def get_context_data(self, **kwargs):
        context = super(Classe_commune, self).get_context_data(**kwargs)
        # categorie = self.kwargs.get("categorie", None)
        # if not categorie:
        #     categorie = self.object.categorie
        categorie = self.Get_categorie()
        infos_categorie = getattr(utils_modeles_documents, categorie.capitalize())().As_dict()
        context['photos_individuelles'] = infos_categorie["photosIndividuelles"]
        context['codes_barres'] = infos_categorie["codesbarres"]
        context['speciaux'] = infos_categorie["speciaux"]
        context['formulaire_champs'] = Formulaire_champs(champs=infos_categorie["champs"])
        return context



class Ajouter(Classe_commune, crud.Ajouter):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres modèles
        if form.instance.defaut:
            self.model.objects.filter(categorie=form.instance.categorie).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Modifier(Classe_commune, crud.Modifier):
    form_class = Formulaire

    def form_valid(self, form):
        # Si le Défaut a été coché, on supprime le Défaut des autres modèles
        if form.instance.defaut:
            self.model.objects.filter(categorie=form.instance.categorie).filter(defaut=True).update(defaut=False)
        return super().form_valid(form)


class Supprimer(Page, crud.Supprimer):
    pass

    def delete(self, request, *args, **kwargs):
        reponse = super(Supprimer, self).delete(request, *args, **kwargs)
        if reponse.status_code != 303:
            # Si le défaut a été supprimé, on le réattribue à un autre modèle
            if len(self.model.objects.filter(categorie=kwargs.get("categorie")).filter(defaut=True)) == 0:
                objet = self.model.objects.filter(categorie=kwargs.get("categorie")).first()
                if objet:
                    objet.defaut = True
                    objet.save()
        return reponse


class Creer(Page, crud.Ajouter):
    form_class = Formulaire_creation
    template_name = "core/crud/edit.html"

    def get_context_data(self, **kwargs):
        context = super(Creer, self).get_context_data(**kwargs)
        context['box_titre'] = "Modèles de documents"
        context['box_introduction'] = "Vous devez saisir le nom du document à créer."
        context['onglet_actif'] = "modeles_documents"
        return context

    def post(self, request, **kwargs):
        nom = request.POST.get("nom")
        categorie = request.POST.get("categorie")
        return HttpResponseRedirect(reverse_lazy("modeles_documents_ajouter", args=(nom, categorie)))


class Dupliquer(Page, crud.Dupliquer):

    def post(self, request, **kwargs):
        # Récupération du modèle à dupliquer
        modele = self.model.objects.get(pk=kwargs.get("pk", None))

        # Duplication du tarif
        nouveau_modele = deepcopy(modele)
        nouveau_modele.pk = None
        nouveau_modele.nom = "Copie de %s" % modele.nom
        nouveau_modele.save()

        # Redirection vers l'objet dupliqué
        if "dupliquer_ouvrir" in request.POST:
            url = reverse(self.url_modifier, args=[nouveau_modele.categorie, nouveau_modele.pk])
        else:
            url = None

        return self.Redirection(url=url)
