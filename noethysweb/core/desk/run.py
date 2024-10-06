#  Copyright (c) 2019-2024 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

import sys, os, subprocess, zipfile, webbrowser, shutil, json
from urllib.request import urlretrieve


class App:
    def __init__(self):
        self.repertoire_app = os.path.dirname(__file__)
        self.virtual_dir = os.path.join(self.repertoire_app, "virtualenv")
        self.virtual_python = os.path.join(self.virtual_dir, "Scripts", "python.exe")
        self.chemin_noethysweb = None
        print("Executable python : ", sys.executable)

    def install_virtual_env(self):
        self.pip_install_package("virtualenv")
        if not os.path.exists(self.virtual_python):
            print("Installation de l'environnement virtuel...")
            subprocess.call([sys.executable, "-m", "virtualenv", self.virtual_dir])
        else:
            print("Virtualenv trouvé : " + self.virtual_python)

    def is_venv(self):
        return sys.prefix == self.virtual_dir

    def restart_under_venv(self):
        print("Redémarrage avec l'environnement virtuel...")
        subprocess.call([self.virtual_python, __file__] + sys.argv[1:])
        exit(0)

    def pip_install_package(self, package):
        try:
            __import__(package)
        except:
            subprocess.call([sys.executable, "-m", "pip", "install", package, "--upgrade"])

    def pip_install_requirements(self, chemin_requirements=None):
        if not chemin_requirements:
            chemin_requirements = os.path.join(self.repertoire_app, "lib", "requirements.txt")
        subprocess.call([sys.executable, "-m", "pip", "install", "-r", chemin_requirements, "--upgrade"])
        self.pip_install_package("django-cryptography-django5")
        self.Remplacer_texte(nom_fichier="virtualenv/Lib/site-packages/upload_form/forms.py", texte="ugettext_lazy", remplacement="gettext_lazy")

    def Remplacer_texte(self, nom_fichier="", texte="", remplacement=""):
        print("Replacement texte dans le fichier %s..." % nom_fichier)
        chemin_fichier = os.path.join(self.repertoire_app, nom_fichier)
        f = open(chemin_fichier, "r")
        filedata = f.read()
        f.close()
        newdata = filedata.replace(texte, remplacement)
        f = open(chemin_fichier, "w")
        f.write(newdata)
        f.close()

    def Download_Noethysweb(self):
        print("Téléchargement de Noethysweb...")
        import requests
        # Lecture du numéro de version online
        try:
            data = requests.get("https://raw.githubusercontent.com/Noethys/Noethysweb/master/noethysweb/versions.txt")
        except:
            print("Le fichier des versions n'a pas pu être téléchargé sur Github.")
            return False
        changelog = data.text
        pos_debut_numVersion = changelog.find("n")
        pos_fin_numVersion = changelog.find("(")
        version_online_txt = changelog[pos_debut_numVersion + 1:pos_fin_numVersion].strip()
        print("version disponible de Noethysweb =" + version_online_txt)

        # Téléchargement du zip
        nom_fichier = "Noethysweb-%s.zip" % version_online_txt
        chemin_fichier_zip = os.path.join(self.repertoire_app, nom_fichier)
        try:
            print("Téléchargement de la version %s..." % version_online_txt)
            urlretrieve("https://github.com/Noethys/Noethysweb/archive/%s.zip" % version_online_txt, chemin_fichier_zip)
        except Exception as err:
            print("Erreur durant le téléchargement de Noethysweb")
            return False

        # Dezippage
        with zipfile.ZipFile(chemin_fichier_zip, "r") as zip:
            zip.extractall(self.repertoire_app)

        # Suppression du zip
        os.remove(chemin_fichier_zip)
        print("Installation de Noethysweb ok.")

    def Get_chemin_noethysweb(self):
        if self.chemin_noethysweb:
            return self.chemin_noethysweb
        for nom in os.listdir(self.repertoire_app):
            if nom.startswith("Noethysweb-"):
                self.chemin_noethysweb = nom
                return nom
        return None

    def run_server(self):
        print("Lancement du serveur django...")
        self.Manage("runserver")

    def Manage(self, commande=""):
        chemin = os.path.join(self.repertoire_app, self.Get_chemin_noethysweb(), "noethysweb", "manage.py")
        subprocess.call([sys.executable, chemin, commande], shell=True)

    def Ouvrir_navigateur(self):
        print("Ouverture du navigateur...")
        print("Si le navigateur ne s'ouvre pas automatiquement, copiez-collez ce lien dans le navigateur : http://127.0.0.1:8000/bureau")
        webbrowser.open("http://127.0.0.1:8000/bureau")

    def Installer_settings_production(self):
        print("Installation du fichier de configuration...")
        chemin_destination = os.path.join(self.repertoire_app, self.Get_chemin_noethysweb(), "noethysweb", "noethysweb", "settings_production.py")
        if not os.path.isfile(chemin_destination):
            # Envoi des settings_production vers le répertoire noethysweb
            shutil.copy(os.path.join(self.repertoire_app, "lib", "settings_modele.py"), chemin_destination)
            # Génération et installation d'un secret key
            from django.core.management.utils import get_random_secret_key
            self.Remplacer_texte(nom_fichier=chemin_destination, texte="{SECRET_KEY}", remplacement=get_random_secret_key())
            # Récupération et installation de l'url gestion
            with open(os.path.join(self.repertoire_app, "preferences.json")) as fichier:
                data = json.load(fichier)
                self.Remplacer_texte(nom_fichier=chemin_destination, texte="{URL_GESTION}", remplacement=data["URL_GESTION"])
            print("Installation du fichier de configuration ok.")

    def Installer_data(self):
        print("Installation des données...")
        # Dézippage du zip data
        with zipfile.ZipFile(os.path.join(self.repertoire_app, "data.zip"), "r") as zip:
            zip.extractall(self.repertoire_app)
        # Installation du json data
        chemin = os.path.join(self.repertoire_app, self.Get_chemin_noethysweb(), "noethysweb", "manage.py")
        subprocess.call([sys.executable, chemin, "loaddata", os.path.join(self.repertoire_app, "data.json")], shell=True)
        # Suppression du fichier json
        os.remove(os.path.join(self.repertoire_app, "data.json"))
        print("Installation des données ok.")

    def Installer_media(self):
        print("Installation des medias...")
        chemin_media = os.path.join(self.repertoire_app, self.Get_chemin_noethysweb(), "noethysweb", "media")
        # Création du répertoire media
        if not os.path.isdir(chemin_media):
            os.mkdir(chemin_media)
        # Dézippage des medias dans le répertoire media
        with zipfile.ZipFile(os.path.join(self.repertoire_app, "media.zip"), "r") as zip:
            zip.extractall(chemin_media)
        print("Installation des medias ok.")

    def Installation_complete(self):
        self.pip_install_package("requests")
        self.Download_Noethysweb()
        self.pip_install_requirements()
        self.Installer_settings_production()
        self.Manage("collectstatic")
        if not os.path.isfile(os.path.join(self.repertoire_app, self.Get_chemin_noethysweb(), "noethysweb", "db.sqlite3")):
            self.Manage("migrate")
            self.Installer_data()
        else:
            print("Warning : La base de données a déjà été initialisée.")
        self.Installer_media()
        print("Fin de l'installation.")

    def run(self):
        # Chargement ou création du virtual environment
        if not self.is_venv():
            self.install_virtual_env()
            self.restart_under_venv()
        else:
            print("Environnement virtuel activé...")
        self.run_menu_principal()

    def run_menu_principal(self):
        # Menu principal
        print("")
        print("----------------- MENU PRINCIPAL -----------------")
        print("1 = Lancer Noethysweb")
        print("2 = Installer Noethysweb")
        print("3 = Commandes avancées")
        print("4 = Quitter")
        reponse = int(input("Quelle action choisissez-vous ? "))

        if reponse == 1:
            if not self.Get_chemin_noethysweb():
                print("Erreur : Noethysweb ne semble pas installé.")
                self.run_menu_principal()
                return
            app.Ouvrir_navigateur()
            app.run_server()
        if reponse == 2:
            if input("Confirmez-vous l'installation (o/n) ? ") == "o":
                print("")
                print("Attention ! Certaines étapes peuvent prendre plusieurs minutes. Veuillez patienter sans interrompre le processus...")
                print("")
                self.Installation_complete()
            self.run_menu_principal()
        if reponse == 3:
            self.run_menu_commandes_avancees()
        if reponse == 4:
            exit()

    def run_menu_commandes_avancees(self):
        print("")
        print("---------------- COMMANDES AVANCEES ----------------")
        print("1 = Télécharger et installer Noethysweb")
        print("2 = Installer les dépendances python")
        print("3 = Installer le fichier de configuration")
        print("4 = Installer les fichiers statiques")
        print("5 = Initialiser la base de données")
        print("6 = Installer les données dans la base de données")
        print("7 = Installer les médias (documents, images, etc...)")
        print("8 = Revenir au menu principal")
        reponse = int(input("Quelle action choisissez-vous ? "))

        if reponse == 1:
            self.Download_Noethysweb()
        if reponse == 2:
            self.pip_install_requirements()
        if reponse == 3:
            self.Installer_settings_production()
        if reponse == 4:
            self.Manage("collectstatic")
        if reponse == 5:
            self.Manage("migrate")
        if reponse == 6:
            self.Installer_data()
        if reponse == 7:
            self.Installer_media()
        self.run_menu_principal()


if __name__ == "__main__":
    app = App()
    app.run()
