# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.urls import reverse_lazy
from core.views import crud
from core.models import Note
from collaborateurs.forms.collaborateur_notes import Formulaire
from collaborateurs.views.collaborateur import Onglet


class Page(Onglet):
    model = Note

    def get_queryset(self):
        # Les objets ne sont accessibles que depuis la fiche de leur collaborateur
        return Note.objects.filter(collaborateur_id=self.Get_idcollaborateur())
    url_liste = "collaborateur_resume"
    description_saisie = "Saisissez le texte de la note, choisissez les utilisateurs qui pourront la consulter et ses options d'affichage, puis cliquez sur le bouton Enregistrer."
    objet_singulier = "une note"
    objet_pluriel = "des notes"

    def get_context_data(self, **kwargs):
        """ Context data spécial pour onglet """
        context = super(Page, self).get_context_data(**kwargs)
        context['box_titre'] = "Note"
        context['onglet_actif'] = "resume"
        return context

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(Page, self).get_form_kwargs(**kwargs)
        form_kwargs["idcollaborateur"] = self.Get_idcollaborateur()
        return form_kwargs

    def get_success_url(self):
        """ Renvoie vers la liste après le formulaire """
        url = self.url_liste
        if "SaveAndNew" in self.request.POST:
            url = self.url_ajouter
        return reverse_lazy(url, kwargs={'idcollaborateur': self.Get_idcollaborateur()})


class Ajouter(Page, crud.Ajouter):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"


class Modifier(Page, crud.Modifier):
    form_class = Formulaire
    template_name = "collaborateurs/collaborateur_edit.html"


class Supprimer(Page, crud.Supprimer):
    template_name = "collaborateurs/collaborateur_delete.html"
