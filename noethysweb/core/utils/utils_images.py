from PIL import Image
import json

# Gestion de la compatibilité pour le filtre (Pillow 8.x gère les deux)
try:
    RESAMPLING_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLING_FILTER = Image.ANTIALIAS


def Recadrer_image_form(cropper_data=None, image=None):
    """ Enregistre l'image d'un form après cropper """
    # 1. On transforme la chaîne JSON en dictionnaire Python
    data = json.loads(cropper_data)

    img = Image.open(image)

    # 2. Rotation
    img = img.rotate(-data["rotate"], expand=True)

    # 3. Recadrage (Crop) basé sur la sélection de l'utilisateur
    img = img.crop((
        data["x"],
        data["y"],
        data["width"] + data["x"],
        data["height"] + data["y"]
    ))

    # 4. Définition des dimensions cibles (Correction du NameError)
    # On utilise 'largeur' envoyé par le widget, ou par défaut la largeur recadrée
    nouvelle_largeur = int(data.get("largeur", data["width"]))

    # On récupère le ratio (soit via le widget, soit via le calcul largeur/hauteur)
    ratio = data.get("ratio", data["width"] / data["height"])

    # Calcul de la hauteur proportionnelle
    nouvelle_hauteur = int(nouvelle_largeur / ratio)

    # 5. Redimensionnement final (pour correspondre au 447x167 attendu)
    img = img.resize((nouvelle_largeur, nouvelle_hauteur), RESAMPLING_FILTER)

    # 6. Sauvegarde
    img.save(image.path)