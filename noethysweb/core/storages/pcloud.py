# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import os.path
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
# from storages.utils import get_available_overwrite_name
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
        repertoire, nom_fichier = os.path.split(self._full_path(name))
        self.client.deletefile(path=repertoire, fileid=self.Get_fileid(name))

    def exists(self, name):
        try:
            return bool(self.Get_meta(name))
        except:
            return False

    def listdir(self, path):
        repertoires, fichiers = [], []
        data = self.client.listfolder(path=self._full_path(path))
        for dict_fichier in data["metadata"]["contents"]:
            if not dict_fichier["isfolder"]:
                fichiers.append(dict_fichier["name"])
        fichiers.sort()
        return repertoires, fichiers

    def Get_fileid(self, path):
        return self.Get_meta(path)["fileid"]

    def Get_meta(self, path):
        repertoire, nom_fichier = os.path.split(path)
        data = self.client.listfolder(path=self._full_path(repertoire))
        for dict_fichier in data["metadata"]["contents"]:
            if dict_fichier["name"] == nom_fichier:
                return dict_fichier
        return None

    def size(self, name):
        return self.Get_meta(name)["size"]

    def modified_time(self, name):
        return self.Get_meta(name)["modified"]

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
        # Incompatible sur django-storages 1.14.4
        # if self.write_mode == 'overwrite':
        #     return get_available_overwrite_name(name, max_length)
        return super().get_available_name(name, max_length)
