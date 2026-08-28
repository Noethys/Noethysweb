FROM python:3.9-slim

# Configuration d'environnement
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=noethysweb.settings

WORKDIR /usr/src/app

# Dépendances système minimales
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation forcée des paquets compatibles avec Django 3.2
COPY ./requirements.txt .
RUN pip install --no-cache-dir django==3.2.25 django-debug-toolbar==3.8.1 django-q2==1.6.2 django-autocomplete-light==3.9.4 psycopg2-binary==2.9.9 gunicorn==21.2.0
RUN pip install --no-cache-dir -r ./requirements.txt

# Copie de tout le code source
COPY . .

WORKDIR /usr/src/app/noethysweb
RUN chmod +x ./manage.py

# Collecte des fichiers statiques pour la production
CMD ["/bin/bash", "-c", "./manage.py collectstatic --noinput && ./manage.py migrate && gunicorn noethysweb.wsgi --bind 0.0.0.0:10000"]

# Commande de démarrage adaptée à Render (Port 10000 requis par défaut)
CMD ["/bin/bash", "-c", "./manage.py migrate && gunicorn noethysweb.wsgi --bind 0.0.0.0:10000"]
