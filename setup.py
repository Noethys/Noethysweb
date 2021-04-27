#  Copyright (c) 2019-2021 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.
import os
from setuptools import setup, find_packages
from noethysweb.noethysweb import version


# Créé un fichier init pour la compilation
f = open("noethysweb/__init__.py", "a")
f.close()

setup(
    name='noethysweb',
    version=version.GetVersion(),
    packages=find_packages(
		exclude=["*/settings_production.py",]
		),
    include_package_data=True,
    license='GNU GPL3',
    author='Ivan LUCAS',
)

# Puis le retire pour éviter un bug avec PyCharm
os.remove("noethysweb/__init__.py")