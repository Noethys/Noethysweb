# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy, reverse
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from core.views.mydatatableview import MyDatatable, columns, helpers
from core.views import crud
from core.models import Album, Photo
from parametrage.forms.albums import Formulaire_album, Formulaire_photo, Formulaire_importation


def Importer_photos_album(request):
    assert request.method == 'POST'
    assert request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    form = Formulaire_importation(request.POST, request.FILES, idalbum=request.POST.get("idalbum"))
    if form.is_valid():
        url = form.form_valid(request)
        return JsonResponse({'action': 'redirect', 'url': url})
    else:
        return JsonResponse({'action': 'replace', 'html': form.as_html(request)})


class Page(crud.Page):
    model = Album
    url_liste = "albums_liste"
    url_ajouter = "albums_ajouter"
    url_modifier = "albums_modifier"
    url_supprimer = "albums_supprimer"
    url_consulter = "albums_consulter"
    description_liste = "Voici ci-dessous la liste des albums photos."
    description_saisie = "Saisissez toutes les informations concernant l'album à créer et cliquez sur le bouton Enregistrer."
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
        context['box_introduction'] = "Vous pouvez ici ajouter des photos à l'album ou modifier les paramètres de l'album."
        context['onglet_actif'] = "albums_liste"
        context['active_checkbox'] = True
        context["hauteur_table"] = "400px"
        context['url_supprimer_plusieurs'] = reverse_lazy(self.url_supprimer_plusieurs, kwargs={"idalbum": self.kwargs["pk"], "listepk": "xxx"})
        context['album'] = Album.objects.get(pk=self.kwargs["pk"])
        context['photos'] = Photo.objects.filter(album_id=self.kwargs["pk"]).order_by("date_creation", "pk")
        context['formulaire_upload'] = Formulaire_importation(idalbum=self.kwargs["pk"])
        context['formulaire_upload_as_html'] = context['formulaire_upload'].as_html(self.request)
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
