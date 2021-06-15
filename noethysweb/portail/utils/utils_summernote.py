# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.forms import fields
import bleach, html
from django_summernote.settings import ALLOWED_TAGS, ATTRIBUTES, STYLES
from django_summernote.widgets import SummernoteInplaceWidget


class SummernoteTextFormField(fields.CharField):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.pop("attrs", {})
        kwargs.update({'widget': SummernoteInplaceWidget(attrs=attrs)})
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        ATTRIBUTES['img'] = ['src', 'style']
        STYLES.extend(["width"])
        return bleach.clean(html.unescape(value), tags=ALLOWED_TAGS, attributes=ATTRIBUTES, styles=STYLES, strip=True, strip_comments=True)
