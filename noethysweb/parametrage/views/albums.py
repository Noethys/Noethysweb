# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import datetime
from PIL import Image
from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Album, Photo
from core.forms.envoi_photos import Formulaire_envoi_photo, Get_contexte_zone_envoi
from parametrage.forms.albums import Formulaire_album, Formulaire_photo


def Lire_date_exif(photo):
    """ Lit la date de prise de vue dans les données EXIF de la photo enregistrée """
    try:
        with photo.fichier.open("rb") as fichier:
            valeur = Image.open(fichier).getexif().get_ifd(0x8769).get(36867)
        return datetime.datetime.strptime(valeur, "%Y:%m:%d %H:%M:%S") if valeur else None
    except Exception:
        return None


def Importer_photos_album(request):
    """ Reçoit une photo envoyée par la zone d'envoi """
    if request.method != "POST":
        return JsonResponse({"ok": False, "erreur": "Requête invalide"}, status=400)
    if not request.user.has_perm("core.albums_liste"):
        return JsonResponse({"ok": False, "erreur": "Vous n'avez pas l'autorisation d'ajouter des photos"}, status=403)
    try:
        idalbum = int(request.POST.get("idalbum", ""))
    except ValueError:
        return JsonResponse({"ok": False, "erreur": "Album introuvable"}, status=400)
    condition_structure = Q(structure__in=request.user.structures.all()) | Q(structure__isnull=True)
    album = Album.objects.filter(condition_structure, pk=idalbum).first()
    if not album:
        return JsonResponse({"ok": False, "erreur": "Album introuvable"}, status=400)
    form = Formulaire_envoi_photo(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "erreur": form.Get_erreur()}, status=400)
    photo = Photo.objects.create(album=album, fichier=form.cleaned_data["fichier"])
    date_creation = form.cleaned_data.get("date_prise") or Lire_date_exif(photo)
    if date_creation:
        photo.date_creation = date_creation
        photo.save(update_fields=["date_creation"])
    return JsonResponse({"ok": True})


class Page(crud.Page):
    model = Album
    url_liste = "albums_liste"
    url_ajouter = "albums_ajouter"
    url_modifier = "albums_modifier"
    url_supprimer = "albums_supprimer"
    url_consulter = "albums_consulter"
    description_liste = "Les albums photos permettent de partager avec les familles les photos des activités. Pour publier un album sur le portail, associez-le à un article (menu Paramétrage > Portail > Articles). Cliquez sur un album pour y ajouter des photos."
    description_saisie = "Saisissez le titre de l'album et, si besoin, sa structure puis cliquez sur le bouton Enregistrer. Vous pourrez ensuite y ajouter des photos."
    objet_singulier = "un album"
    objet_pluriel = "des albums"
    boutons_liste = [
        {"label": "Ajouter", "classe": "btn btn-success", "href": reverse_lazy(url_ajouter), "icone": "fa fa-plus"},
    ]


class Liste(Page, crud.Liste):
    model = Album

    def get_queryset(self):
        return Album.objects.filter(self.Get_filtres("Q"), self.Get_condition_structure()).annotate(nbre_photos=Count("photo"))

    def get_context_data(self, **kwargs):
        context = super(Liste, self).get_context_data(**kwargs)
        context['impression_introduction'] = ""
        context['impression_conclusion'] = ""
        context['afficher_menu_brothers'] = True
        return context

    class datatable_class(MyDatatable):
        filtres = ["idalbum", "titre", "date_creation"]
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')
        nbre_photos = columns.TextColumn("Nbre de photos", sources="nbre_photos")

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["idalbum", "titre", "nbre_photos", "date_creation"]
            processors = {
                'date_creation': helpers.format_date('%d/%m/%Y %H:%M'),
            }
            ordering = ["date_creation"]

        def Get_actions_speciales(self, instance, *args, **kwargs):
            view = kwargs["view"]
            html = [
                self.Create_bouton_modifier(url=reverse(view.url_consulter, args=[instance.pk])),
                self.Create_bouton_supprimer(url=reverse(view.url_supprimer, args=[instance.pk])),
            ]
            return self.Create_boutons_actions(html)


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire_album

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.object.idalbum})


class Modifier(Page, crud.Modifier):
    form_class = Formulaire_album

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['pk']})


class Supprimer(Page, crud.Supprimer):
    pass


class Consulter(Page, crud.Liste):
    template_name = "parametrage/albums.html"
    mode = "CONSULTATION"
    model = Photo
    boutons_liste = []
    url_supprimer_plusieurs = "albums_supprimer_plusieurs_photos"

    def get_queryset(self):
        return Photo.objects.filter(self.Get_filtres("Q"), album_id=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super(Consulter, self).get_context_data(**kwargs)
        context['box_titre'] = "Consulter un album"
        context['box_introduction'] = "Ajoutez des photos à l'album en les important depuis votre ordinateur, ou modifiez les paramètres de l'album. Pensez à vérifier que les familles ont donné leur accord pour la diffusion des photos de leurs enfants."
        context['onglet_actif'] = "albums_liste"
        context['active_checkbox'] = True
        context["hauteur_table"] = "400px"
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idalbum": self.kwargs["pk"], "listepk": "xxx"})
        context['album'] = Album.objects.get(pk=self.kwargs["pk"])
        context['photos'] = Photo.objects.filter(album_id=self.kwargs["pk"]).order_by("date_creation", "pk")
        context['zone_envoi'] = Get_contexte_zone_envoi(url=reverse("ajax_importer_photos_album"), libelle_bouton="Envoyer",
                                                        url_fin=reverse(self.url_consulter, kwargs={"pk": self.kwargs["pk"]}), extra={"idalbum": self.kwargs["pk"]})
        return context

    def post(self, request, *args, **kwargs):
        """ Importation de nouvelles photos """
        fichiers = request.FILES.getlist("fichier")
        for fichier in fichiers:
            Photo.objects.create(album_id=self.kwargs["pk"], fichier=fichier)
        return HttpResponseRedirect(reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["pk"]}))

    class datatable_class(MyDatatable):
        filtres = ["idphoto", "titre", "date_creation"]
        check = columns.CheckBoxSelectColumn(label="")
        image = columns.DisplayColumn("Image", sources="image", processor='Get_image')
        actions = columns.TextColumn("Actions", sources=None, processor='Get_actions_speciales')

        class Meta:
            structure_template = MyDatatable.structure_template
            columns = ["check", "idphoto", "image", "titre", "date_creation", "actions"]
            ordering = ["date_creation", "idphoto"]
            processors = {
                'date_creation': helpers.format_date('%d/%m/%Y %H:%M'),
            }

        def Get_image(self, instance, **kwargs):
            if instance.fichier:
                return """
                    <a href="%s" data-toggle="lightbox" data-title="%s" data-gallery="gallery">
                        <img class="img-fluid img-thumbnail" style="max-height: 100px;" src="%s">
                    </a>
                """ % (instance.fichier.url, instance.titre or "Sans titre", instance.fichier.url)
            return ""

        def Get_actions_speciales(self, instance, *args, **kwargs):
            html = [
                self.Create_bouton_modifier(url=reverse("albums_modifier_photo", kwargs={"idalbum": instance.album_id, "pk": instance.pk})),
                self.Create_bouton_supprimer(url=reverse("albums_supprimer_photo", kwargs={"idalbum": instance.album_id, "pk": instance.pk})),
            ]
            return self.Create_boutons_actions(html)


class Modifier_photo(Page, crud.Modifier):
    form_class = Formulaire_photo
    model = Photo

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={'pk': self.kwargs['idalbum']})


class Supprimer_photo(Page, crud.Supprimer):
    model = Photo
    objet_singulier = "une photo"

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idalbum"]})


class Supprimer_plusieurs_photos(Page, crud.Supprimer_plusieurs):
    model = Photo
    objet_pluriel = "des photos"

    def get_success_url(self):
        return reverse_lazy(self.url_consulter, kwargs={"pk": self.kwargs["idalbum"]})
