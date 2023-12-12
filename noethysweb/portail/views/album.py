# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from portail.views.base import CustomView
from core.models import Album, Photo


class View(CustomView, TemplateView):
    template_name = "portail/album.html"
    menu_code = "portail_album"

    def get_context_data(self, **kwargs):
        context = super(View, self).get_context_data(**kwargs)
        context['page_titre'] = _("Album")
        context["album"] = Album.objects.get(code=kwargs.get("code", None))
        context["photos"] = Photo.objects.filter(album=context["album"]).order_by("date_creation")
        return context
