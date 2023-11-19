# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django_select2.forms import Select2Widget as Select2WidgetBase
from django_select2.forms import Select2MultipleWidget as Select2MultipleWidgetBase


class Select2Widget(Select2WidgetBase):
    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs["lang"] = "fr"
        attrs["data-width"] = "100%"
        attrs["data-theme"] = "bootstrap4"
        return attrs


class Select2MultipleWidget(Select2MultipleWidgetBase):
    def build_attrs(self, *args, **kwargs):
        attrs = super().build_attrs(*args, **kwargs)
        attrs["lang"] = "fr"
        attrs["data-width"] = "100%"
        # attrs["data-theme"] = "bootstrap4"
        return attrs
