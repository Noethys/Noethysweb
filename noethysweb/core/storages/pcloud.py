# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from storages.utils import get_available_overwrite_name
from storages.utils import setting
from pcloud import PyCloud

_DEFAULT_MODE = 'add'


@deconstructible
class PcloudStorage(Storage):
    """ Pcloud Storage class for Django pluggable storage system."""
    location = setting("PCLOUD_ROOT_PATH", "/")
    app_key = setting("PCLOUD_APP_KEY")
    app_secret = setting("PCLOUD_APP_SECRET")
    write_mode = setting("PCLOUD_WRITE_MODE", _DEFAULT_MODE)

    def __init__(
        self,
        root_path=location,
        write_mode=write_mode,
        app_key=app_key,
        app_secret=app_secret,
    ):
        self.root_path = root_path
        self.write_mode = write_mode
        self.client = PyCloud(app_key, app_secret, endpoint="eapi")

    def _full_path(self, name):
        if name == '/':
            name = ''
        full_path = self.root_path
        if name:
            full_path += "/" + name
        return full_path

    def delete(self, name):
        self.client.deletefile(self._full_path(name))

    def exists(self, name):
        try:
            return bool(self.Get_metadata_fichier(name))
        except:
            return False

    def listdir(self, path):
        repertoires, fichiers = [], []
        data = self.client.listfolder(path=self._full_path(path))
        for dict_fichier in data["metadata"]["contents"]:
            if not dict_fichier["isfolder"]:
                fichiers.append(dict_fichier["name"])
        return repertoires, fichiers

    def Get_metadata_fichier(self, name):
        return self.client.stat(self._full_path(name))

    def size(self, name):
        return self.Get_metadata_fichier(name)["size"]

    def modified_time(self, name):
        return self.Get_metadata_fichier(name)["modified"]

    def url(self, name):
        pass

    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        content.open()
        self.client.uploadfile(data=content.read(), filename=name, path=self.root_path)
        content.close()
        return name.lstrip(self.root_path)

    def get_available_name(self, name, max_length=None):
        """Overwrite existing file with the same name."""
        name = self._full_path(name)
        if self.write_mode == 'overwrite':
            return get_available_overwrite_name(name, max_length)
        return super().get_available_name(name, max_length)
